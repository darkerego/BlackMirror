from socket import SHUT_RDWR, SOL_TCP, TCP_NODELAY, socket
import time
from typing import Iterator, Union
from gevent.lock import BoundedSemaphore
from simplefix import FixMessage, FixParser
from werkzeug.datastructures import ImmutableMultiDict
from contextlib import ExitStack, closing
from datetime import datetime
from decimal import Decimal
import hmac
import logging
import socket
import ssl
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

import gevent
from gevent.event import Event
import simplefix
from simplefix.message import fix_val

logger = logging.getLogger(__name__)



class FixConnection:
    def __init__(self, sock: socket, sender_id: str, target_id: Optional[str] = None) -> None:
        self._sock = sock
        sock.setsockopt(SOL_TCP, TCP_NODELAY, 1)
        self._next_send_seq_num = 1
        self._next_recv_seq_num = 1
        self._sender_id = sender_id
        self._target_id = target_id
        self._last_send_time = time.time()
        self._last_recv_time = time.time()
        self._heartbeat_interval = 30.
        self._has_session = False
        self._disconnected = Event()
        self._send_lock = BoundedSemaphore(1)

        gevent.spawn(self._close_on_exit)

        self.messages = self._get_messages()

    @property
    def connected(self) -> bool:
        return not self._disconnected.is_set()

    def _get_messages(self) -> Iterator[FixMessage]:
        try:
            for msg in self._read_messages():
                if not self._validate_message(msg):
                    continue

                if msg.message_type == simplefix.MSGTYPE_HEARTBEAT:
                    pass
                elif msg.message_type == simplefix.MSGTYPE_TEST_REQUEST:
                    self._send_heartbeat(msg.get(simplefix.TAG_TESTREQID))
                elif msg.message_type == simplefix.MSGTYPE_LOGOUT:
                    self.close()
                else:
                    yield msg
        finally:
            self.close()

    def _read_messages(self) -> Iterator[FixMessage]:
        parser = FixParser()
        while True:
            try:
                buf = self._sock.recv(4096)
            except OSError:
                return
            if not buf:
                return
            parser.append_buffer(buf)

            while True:
                try:
                    msg = parser.get_message()
                except Exception:
                    logger.warning('Error parsing FIX message', exc_info=True)
                    return
                if msg is None:
                    break
                yield msg

    def _validate_message(self, msg: FixMessage) -> bool:
        try:
            # Hack to make msg.get return decoded strings.
            decoded = ImmutableMultiDict([(k, v.decode()) for k, v in msg.pairs])
            msg.get = lambda key: decoded.get(fix_val(key))
        except ValueError:
            self.reject_message(
                msg, reason='Invalid encoding',
                error_code=simplefix.SESSIONREJECTREASON_INCOORECT_DATA_FORMAT_FOR_VALUE,
            )
            return False

        if self._target_id is None and msg.get(simplefix.TAG_SENDER_COMPID):
            self._target_id = msg.get(simplefix.TAG_SENDER_COMPID)

        if msg.get(simplefix.TAG_MSGSEQNUM):
            if msg.get(simplefix.TAG_MSGSEQNUM) == str(self._next_recv_seq_num):
                self._next_recv_seq_num += 1
            else:
                self.reject_message(
                    msg, reason='Incorrect sequence number',
                    tag_id=simplefix.TAG_MSGSEQNUM,
                    error_code=simplefix.SESSIONREJECTREASON_VALUE_INCORRECT_FOR_THIS_TAG)
                return False

        for tag, description in [(simplefix.TAG_MSGTYPE, 'message type'),
                                 (simplefix.TAG_BEGINSTRING, 'begin string'),
                                 (simplefix.TAG_SENDER_COMPID, 'sender ID'),
                                 (simplefix.TAG_TARGET_COMPID, 'target ID'),
                                 (simplefix.TAG_SENDING_TIME, 'sending time'),
                                 (simplefix.TAG_MSGSEQNUM, 'sequence number'),
                                 ]:
            if not msg.get(tag):
                self.reject_message(msg, reason=f'Missing {description}',
                                    tag_id=tag,
                                    error_code=simplefix.SESSIONREJECTREASON_REQUIRED_TAG_MISSING)
                return False

        if msg.get(simplefix.TAG_BEGINSTRING) != 'FIX.4.2':
            self.reject_message(
                msg, reason='Invalid FIX version',
                tag_id=simplefix.TAG_BEGINSTRING,
                error_code=simplefix.SESSIONREJECTREASON_VALUE_INCORRECT_FOR_THIS_TAG)
            return False
        elif msg.get(simplefix.TAG_SENDER_COMPID) != self._target_id:
            self.reject_message(
                msg, reason='Incorrect sender',
                tag_id=simplefix.TAG_SENDER_COMPID,
                error_code=simplefix.SESSIONREJECTREASON_VALUE_INCORRECT_FOR_THIS_TAG)
            return False
        elif msg.get(simplefix.TAG_TARGET_COMPID) != self._sender_id:
            self.reject_message(
                msg, reason='Incorrect target',
                tag_id=simplefix.TAG_TARGET_COMPID,
                error_code=simplefix.SESSIONREJECTREASON_VALUE_INCORRECT_FOR_THIS_TAG)
            return False

        self._last_recv_time = time.time()

        return True

    def send(self, values: dict) -> None:
        with self._send_lock:
            msg = FixMessage()
            msg.append_pair(simplefix.TAG_BEGINSTRING, 'FIX.4.2')
            msg.append_pair(simplefix.TAG_SENDER_COMPID, self._sender_id)
            msg.append_pair(simplefix.TAG_TARGET_COMPID, self._target_id)
            msg.append_pair(simplefix.TAG_MSGSEQNUM, self._next_send_seq_num)
            for key, value in values.items():
                if isinstance(value, datetime):
                    msg.append_utc_timestamp(key, value)
                else:
                    msg.append_pair(key, value)
            if not msg.get(simplefix.TAG_SENDING_TIME):
                msg.append_utc_timestamp(simplefix.TAG_SENDING_TIME)
            encoded = msg.encode()
            self._last_send_time = time.time()
            self._next_send_seq_num += 1

            try:
                print('send', encoded.replace(b'\x01', b'|'))
                self._sock.sendall(encoded)
            except OSError:
                self.close(clean=False)
                return

            if msg.message_type == simplefix.MSGTYPE_LOGON:
                self._has_session = True

    def reject_message(self, msg: FixMessage, reason: str, *,
                       tag_id: Optional[Union[bytes, int]] = None,
                       error_code: Union[bytes, int]) -> None:
        params = {
            simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_REJECT,
            simplefix.TAG_REFSEQNUM: msg.get(simplefix.TAG_MSGSEQNUM),
            372: msg.message_type,
            simplefix.TAG_TEXT: reason,
            simplefix.TAG_SESSIONREJECTREASON: error_code,
        }
        if tag_id is not None:
            params[371] = tag_id
        self.send(params)

    # Run this every few seconds
    def _maybe_send_heartbeat(self) -> None:
        if time.time() - self._last_send_time > self._heartbeat_interval:
            self._send_heartbeat()

    def _send_heartbeat(self, test_req_id: Optional[str] = None) -> None:
        if not self._has_session:
            return
        data = {
            simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_HEARTBEAT,
        }
        if test_req_id:
            data[simplefix.TAG_TESTREQID] = test_req_id
        self.send(data)

    # Run this every few seconds
    def _check_last_message_time(self) -> None:
        elapsed = time.time() - self._last_recv_time
        if elapsed > self._heartbeat_interval + 10:
            self.close()
        elif elapsed > self._heartbeat_interval and self._has_session:
            self.send({
                simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_TEST_REQUEST,
                simplefix.TAG_TESTREQID: datetime.now(),
            })

    def close(self, clean: bool = True) -> None:
        if self._disconnected.is_set():
            return
        self._disconnected.set()
        if clean and self._has_session:
            self._has_session = False
            self.send({
                simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_LOGOUT,
            })
            try:
                self._sock.shutdown(SHUT_RDWR)
            except OSError:
                self._sock.close()
        else:
            self._sock.close()

    def _close_on_exit(self) -> None:
        gevent.wait([self._disconnected], count=1)
        if self.connected:
            self.close()



class FixClient:
    """FIX client to use for testing."""

    def __init__(self, url: str, client_id: str, target_id: str,
                 subaccount_name: Optional[str] = None) -> None:
        self._url = url
        self._client_id = client_id
        self._target_id = target_id
        self._conn: Optional[FixConnection] = None
        self._connected = Event()
        self._next_seq_num = 1
        self._have_connected = False
        self._subaccount_name = subaccount_name

    def connect(self) -> None:
        if self._have_connected:
            return
        runner = gevent.spawn(self.run)
        gevent.wait([runner, self._connected], count=1)
        if runner.exception:
            runner.get()
        assert self._connected.is_set()
        self._have_connected = True

    def run(self) -> None:
        parsed_url = urlparse(self._url)
        with ExitStack() as stack:
            sock = stack.enter_context(socket.create_connection((parsed_url.hostname,
                                                                 parsed_url.port)))
            if 'ssl' in parsed_url.scheme or 'tls' in parsed_url.scheme:
                context = ssl.create_default_context()
                sock = stack.enter_context(context.wrap_socket(sock,
                                                               server_hostname=parsed_url.hostname))
            conn: FixConnection = stack.enter_context(
                closing(FixConnection(sock, self._client_id, self._target_id)))
            self._conn = conn
            self._connected.set()

            for msg in conn.messages:
                print(msg)
            logger.info('Disconnected')

    def send(self, values: dict) -> None:
        self.connect()
        assert self._connected.is_set()
        assert self._conn is not None
        self._conn.send(values)

    def login(self, secret: str, cancel_on_disconnect: Optional[str] = None) -> None:
        send_time_str = datetime.now().strftime('%Y%m%d-%H:%M:%S')
        sign_target = b'\x01'.join([fix_val(val) for val in [
            send_time_str,
            simplefix.MSGTYPE_LOGON,
            self._next_seq_num,
            self._client_id,
            self._target_id,
        ]])
        signed = hmac.new(secret.encode(), sign_target, 'sha256').hexdigest()
        self.send({
            simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_LOGON,
            simplefix.TAG_SENDING_TIME: send_time_str,
            simplefix.TAG_ENCRYPTMETHOD: 0,
            simplefix.TAG_HEARTBTINT: 30,
            simplefix.TAG_RAWDATA: signed,
            **({8013: cancel_on_disconnect} if cancel_on_disconnect else {}),
            **({simplefix.TAG_ACCOUNT: self._subaccount_name} if self._subaccount_name else {}),
        })

    def send_heartbeat(self, test_req_id: Optional[str] = None) -> None:
        req = {
            simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_HEARTBEAT,
        }
        if test_req_id:
            req[simplefix.TAG_TESTREQID] = test_req_id
        self.send(req)

    def send_test_request(self, test_req_id: str) -> None:
        self.send({
            simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_TEST_REQUEST,
            simplefix.TAG_TESTREQID: test_req_id,
        })

    def request_order_status(self, order_id: str) -> None:
        self.send({
            simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_ORDER_STATUS_REQUEST,
            simplefix.TAG_ORDERID: order_id,
        })

    def cancel_all_limit_orders(self, market: Optional[str] = None,
                                client_cancel_id: Optional[str] = None) -> None:
        self.send({
            simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_ORDER_MASS_CANCEL_REQUEST,
            530: 1 if market else 7,
            **({simplefix.TAG_CLORDID: client_cancel_id} if client_cancel_id else {}),
            **({simplefix.TAG_SYMBOL: market} if market else {}),
        })

    def send_order(self, symbol: str, side: str, price: Decimal, size: Decimal,
                   reduce_only: bool = False, client_order_id: Optional[str] = None,
                   ioc: bool = False) -> None:
        self.send({
            simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_NEW_ORDER_SINGLE,
            simplefix.TAG_HANDLINST: simplefix.HANDLINST_AUTO_PRIVATE,
            simplefix.TAG_CLORDID: uuid4() if client_order_id is None else client_order_id,
            simplefix.TAG_SYMBOL: symbol,
            simplefix.TAG_SIDE: (simplefix.SIDE_BUY if side == 'buy'
                                 else simplefix.SIDE_SELL),
            simplefix.TAG_PRICE: price,
            simplefix.TAG_ORDERQTY: size,
            simplefix.TAG_ORDTYPE: simplefix.ORDTYPE_LIMIT,
            simplefix.TAG_TIMEINFORCE: simplefix.TIMEINFORCE_GOOD_TILL_CANCEL if not ioc else \
                simplefix.TIMEINFORCE_IMMEDIATE_OR_CANCEL,
            **({simplefix.TAG_EXECINST: simplefix.EXECINST_DO_NOT_INCREASE} if reduce_only else {}),
        })

    def cancel_order(self, order_id: Optional[str] = None,
                     client_order_id: Optional[str] = None) -> None:
        req = {
            simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_ORDER_CANCEL_REQUEST,
        }
        if order_id is not None:
            req[simplefix.TAG_ORDERID] = order_id
        if client_order_id is not None:
            req[simplefix.TAG_CLORDID] = client_order_id
        self.send(req)


# To start up:
# secret = ''
# api_key = ''
# client = FixClient('tcp+ssl://fix.ftx_lib.com:4363', target_id='FTX', client_id=api_key)
# client.login(secret)
