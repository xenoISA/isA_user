import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BaseResponse(_message.Message):
    __slots__ = ("success", "message", "error_code", "error_message", "timestamp", "trace_id")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    error_code: str
    error_message: str
    timestamp: _timestamp_pb2.Timestamp
    trace_id: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., error_code: _Optional[str] = ..., error_message: _Optional[str] = ..., timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., trace_id: _Optional[str] = ...) -> None: ...

class User(_message.Message):
    __slots__ = ("user_id", "auth0_id", "email", "name", "organization_id", "created_at", "is_active", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    AUTH0_ID_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    auth0_id: str
    email: str
    name: str
    organization_id: str
    created_at: _timestamp_pb2.Timestamp
    is_active: bool
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, user_id: _Optional[str] = ..., auth0_id: _Optional[str] = ..., email: _Optional[str] = ..., name: _Optional[str] = ..., organization_id: _Optional[str] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., is_active: bool = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class Organization(_message.Message):
    __slots__ = ("organization_id", "name", "display_name", "type", "plan", "created_at", "is_active")
    ORGANIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PLAN_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    organization_id: str
    name: str
    display_name: str
    type: str
    plan: str
    created_at: _timestamp_pb2.Timestamp
    is_active: bool
    def __init__(self, organization_id: _Optional[str] = ..., name: _Optional[str] = ..., display_name: _Optional[str] = ..., type: _Optional[str] = ..., plan: _Optional[str] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., is_active: bool = ...) -> None: ...

class AuthContext(_message.Message):
    __slots__ = ("user", "organization", "permissions", "access_token", "expires_at", "provider")
    USER_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    PERMISSIONS_FIELD_NUMBER: _ClassVar[int]
    ACCESS_TOKEN_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    user: User
    organization: Organization
    permissions: _containers.RepeatedScalarFieldContainer[str]
    access_token: str
    expires_at: _timestamp_pb2.Timestamp
    provider: str
    def __init__(self, user: _Optional[_Union[User, _Mapping]] = ..., organization: _Optional[_Union[Organization, _Mapping]] = ..., permissions: _Optional[_Iterable[str]] = ..., access_token: _Optional[str] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., provider: _Optional[str] = ...) -> None: ...

class RequestContext(_message.Message):
    __slots__ = ("request_id", "trace_id", "user_id", "organization_id", "service_name", "method_name", "start_time", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    SERVICE_NAME_FIELD_NUMBER: _ClassVar[int]
    METHOD_NAME_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    trace_id: str
    user_id: str
    organization_id: str
    service_name: str
    method_name: str
    start_time: _timestamp_pb2.Timestamp
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, request_id: _Optional[str] = ..., trace_id: _Optional[str] = ..., user_id: _Optional[str] = ..., organization_id: _Optional[str] = ..., service_name: _Optional[str] = ..., method_name: _Optional[str] = ..., start_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...
