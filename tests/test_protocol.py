import pytest

from kvstore.commands import Command
from kvstore.errors import ProtocolError
from kvstore.protocol import MAX_REQUEST_BYTES, Request, Response, parse_request


def test_parse_valid_set_request():
    request = parse_request('{"command":"SET","key":"name","value":"Player"}')
    assert request == Request(command=Command.SET, key="name", value="Player")


def test_parse_valid_get_request():
    request = parse_request('{"command":"GET","key":"name"}')
    assert request == Request(command=Command.GET, key="name")


def test_malformed_json_raises_protocol_error():
    with pytest.raises(ProtocolError) as exc_info:
        parse_request("{not json")
    assert exc_info.value.code == "malformed_json"


def test_unknown_command_raises_protocol_error():
    with pytest.raises(ProtocolError) as exc_info:
        parse_request('{"command":"FOO","key":"name"}')
    assert exc_info.value.code == "unknown_command"


def test_missing_required_field_raises_protocol_error():
    with pytest.raises(ProtocolError) as exc_info:
        parse_request('{"command":"SET","key":"name"}')
    assert exc_info.value.code == "missing_field:value"


def test_incorrect_field_type_raises_protocol_error():
    with pytest.raises(ProtocolError) as exc_info:
        parse_request('{"command":"SET","key":"name","value":123}')
    assert exc_info.value.code == "invalid_field_type:value"


def test_oversized_request_raises_protocol_error():
    huge_value = "x" * MAX_REQUEST_BYTES
    with pytest.raises(ProtocolError) as exc_info:
        parse_request(
            f'{{"command":"SET","key":"name","value":"{huge_value}"}}'
        )
    assert exc_info.value.code == "request_too_large"


def test_response_to_json_line_only_includes_set_fields():
    response = Response(status="success", value="Player")
    assert response.to_json_line() == '{"status": "success", "value": "Player"}'