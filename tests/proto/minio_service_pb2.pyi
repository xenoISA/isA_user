import datetime

import common_pb2 as _common_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BucketPolicyType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BUCKET_POLICY_PRIVATE: _ClassVar[BucketPolicyType]
    BUCKET_POLICY_PUBLIC_READ: _ClassVar[BucketPolicyType]
    BUCKET_POLICY_PUBLIC_WRITE: _ClassVar[BucketPolicyType]
    BUCKET_POLICY_PUBLIC_RW: _ClassVar[BucketPolicyType]
    BUCKET_POLICY_CUSTOM: _ClassVar[BucketPolicyType]
BUCKET_POLICY_PRIVATE: BucketPolicyType
BUCKET_POLICY_PUBLIC_READ: BucketPolicyType
BUCKET_POLICY_PUBLIC_WRITE: BucketPolicyType
BUCKET_POLICY_PUBLIC_RW: BucketPolicyType
BUCKET_POLICY_CUSTOM: BucketPolicyType

class BucketInfo(_message.Message):
    __slots__ = ("name", "creation_date", "owner_id", "organization_id", "tags", "region", "size_bytes", "object_count")
    class TagsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREATION_DATE_FIELD_NUMBER: _ClassVar[int]
    OWNER_ID_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    REGION_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_COUNT_FIELD_NUMBER: _ClassVar[int]
    name: str
    creation_date: _timestamp_pb2.Timestamp
    owner_id: str
    organization_id: str
    tags: _containers.ScalarMap[str, str]
    region: str
    size_bytes: int
    object_count: int
    def __init__(self, name: _Optional[str] = ..., creation_date: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., owner_id: _Optional[str] = ..., organization_id: _Optional[str] = ..., tags: _Optional[_Mapping[str, str]] = ..., region: _Optional[str] = ..., size_bytes: _Optional[int] = ..., object_count: _Optional[int] = ...) -> None: ...

class ObjectInfo(_message.Message):
    __slots__ = ("key", "size", "etag", "content_type", "last_modified", "metadata", "storage_class", "version_id", "owner_id")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    KEY_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    ETAG_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    LAST_MODIFIED_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    STORAGE_CLASS_FIELD_NUMBER: _ClassVar[int]
    VERSION_ID_FIELD_NUMBER: _ClassVar[int]
    OWNER_ID_FIELD_NUMBER: _ClassVar[int]
    key: str
    size: int
    etag: str
    content_type: str
    last_modified: _timestamp_pb2.Timestamp
    metadata: _containers.ScalarMap[str, str]
    storage_class: str
    version_id: str
    owner_id: str
    def __init__(self, key: _Optional[str] = ..., size: _Optional[int] = ..., etag: _Optional[str] = ..., content_type: _Optional[str] = ..., last_modified: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., metadata: _Optional[_Mapping[str, str]] = ..., storage_class: _Optional[str] = ..., version_id: _Optional[str] = ..., owner_id: _Optional[str] = ...) -> None: ...

class CreateBucketRequest(_message.Message):
    __slots__ = ("bucket_name", "user_id", "organization_id", "region", "object_locking", "tags")
    class TagsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    REGION_FIELD_NUMBER: _ClassVar[int]
    OBJECT_LOCKING_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    user_id: str
    organization_id: str
    region: str
    object_locking: bool
    tags: _containers.ScalarMap[str, str]
    def __init__(self, bucket_name: _Optional[str] = ..., user_id: _Optional[str] = ..., organization_id: _Optional[str] = ..., region: _Optional[str] = ..., object_locking: bool = ..., tags: _Optional[_Mapping[str, str]] = ...) -> None: ...

class CreateBucketResponse(_message.Message):
    __slots__ = ("success", "message", "bucket_info", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    BUCKET_INFO_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    bucket_info: BucketInfo
    error: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., bucket_info: _Optional[_Union[BucketInfo, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class ListBucketsRequest(_message.Message):
    __slots__ = ("user_id", "organization_id", "prefix")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    PREFIX_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    organization_id: str
    prefix: str
    def __init__(self, user_id: _Optional[str] = ..., organization_id: _Optional[str] = ..., prefix: _Optional[str] = ...) -> None: ...

class ListBucketsResponse(_message.Message):
    __slots__ = ("success", "buckets", "total_count", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    BUCKETS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    buckets: _containers.RepeatedCompositeFieldContainer[BucketInfo]
    total_count: int
    error: str
    def __init__(self, success: bool = ..., buckets: _Optional[_Iterable[_Union[BucketInfo, _Mapping]]] = ..., total_count: _Optional[int] = ..., error: _Optional[str] = ...) -> None: ...

class DeleteBucketRequest(_message.Message):
    __slots__ = ("bucket_name", "user_id", "force")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    FORCE_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    user_id: str
    force: bool
    def __init__(self, bucket_name: _Optional[str] = ..., user_id: _Optional[str] = ..., force: bool = ...) -> None: ...

class DeleteBucketResponse(_message.Message):
    __slots__ = ("success", "message", "deleted_objects", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DELETED_OBJECTS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    deleted_objects: int
    error: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., deleted_objects: _Optional[int] = ..., error: _Optional[str] = ...) -> None: ...

class GetBucketInfoRequest(_message.Message):
    __slots__ = ("bucket_name", "user_id")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    user_id: str
    def __init__(self, bucket_name: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class GetBucketInfoResponse(_message.Message):
    __slots__ = ("success", "bucket_info", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    BUCKET_INFO_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    bucket_info: BucketInfo
    error: str
    def __init__(self, success: bool = ..., bucket_info: _Optional[_Union[BucketInfo, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class SetBucketPolicyRequest(_message.Message):
    __slots__ = ("bucket_name", "user_id", "policy_type", "custom_policy")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    POLICY_TYPE_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_POLICY_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    user_id: str
    policy_type: BucketPolicyType
    custom_policy: str
    def __init__(self, bucket_name: _Optional[str] = ..., user_id: _Optional[str] = ..., policy_type: _Optional[_Union[BucketPolicyType, str]] = ..., custom_policy: _Optional[str] = ...) -> None: ...

class SetBucketPolicyResponse(_message.Message):
    __slots__ = ("success", "message", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    error: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class GetBucketPolicyRequest(_message.Message):
    __slots__ = ("bucket_name", "user_id")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    user_id: str
    def __init__(self, bucket_name: _Optional[str] = ..., user_id: _Optional[str] = ...) -> None: ...

class GetBucketPolicyResponse(_message.Message):
    __slots__ = ("success", "policy_type", "policy_json", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    POLICY_TYPE_FIELD_NUMBER: _ClassVar[int]
    POLICY_JSON_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    policy_type: BucketPolicyType
    policy_json: str
    error: str
    def __init__(self, success: bool = ..., policy_type: _Optional[_Union[BucketPolicyType, str]] = ..., policy_json: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class PutObjectRequest(_message.Message):
    __slots__ = ("metadata", "chunk")
    METADATA_FIELD_NUMBER: _ClassVar[int]
    CHUNK_FIELD_NUMBER: _ClassVar[int]
    metadata: PutObjectMetadata
    chunk: bytes
    def __init__(self, metadata: _Optional[_Union[PutObjectMetadata, _Mapping]] = ..., chunk: _Optional[bytes] = ...) -> None: ...

class PutObjectMetadata(_message.Message):
    __slots__ = ("bucket_name", "object_key", "user_id", "content_type", "content_length", "metadata", "storage_class")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_LENGTH_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    STORAGE_CLASS_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_key: str
    user_id: str
    content_type: str
    content_length: int
    metadata: _containers.ScalarMap[str, str]
    storage_class: str
    def __init__(self, bucket_name: _Optional[str] = ..., object_key: _Optional[str] = ..., user_id: _Optional[str] = ..., content_type: _Optional[str] = ..., content_length: _Optional[int] = ..., metadata: _Optional[_Mapping[str, str]] = ..., storage_class: _Optional[str] = ...) -> None: ...

class PutObjectResponse(_message.Message):
    __slots__ = ("success", "object_key", "etag", "version_id", "size", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    ETAG_FIELD_NUMBER: _ClassVar[int]
    VERSION_ID_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    object_key: str
    etag: str
    version_id: str
    size: int
    error: str
    def __init__(self, success: bool = ..., object_key: _Optional[str] = ..., etag: _Optional[str] = ..., version_id: _Optional[str] = ..., size: _Optional[int] = ..., error: _Optional[str] = ...) -> None: ...

class GetObjectRequest(_message.Message):
    __slots__ = ("bucket_name", "object_key", "user_id", "offset", "length", "version_id")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    VERSION_ID_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_key: str
    user_id: str
    offset: int
    length: int
    version_id: str
    def __init__(self, bucket_name: _Optional[str] = ..., object_key: _Optional[str] = ..., user_id: _Optional[str] = ..., offset: _Optional[int] = ..., length: _Optional[int] = ..., version_id: _Optional[str] = ...) -> None: ...

class GetObjectResponse(_message.Message):
    __slots__ = ("metadata", "chunk")
    METADATA_FIELD_NUMBER: _ClassVar[int]
    CHUNK_FIELD_NUMBER: _ClassVar[int]
    metadata: ObjectInfo
    chunk: bytes
    def __init__(self, metadata: _Optional[_Union[ObjectInfo, _Mapping]] = ..., chunk: _Optional[bytes] = ...) -> None: ...

class DeleteObjectRequest(_message.Message):
    __slots__ = ("bucket_name", "object_key", "user_id", "version_id")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_ID_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_key: str
    user_id: str
    version_id: str
    def __init__(self, bucket_name: _Optional[str] = ..., object_key: _Optional[str] = ..., user_id: _Optional[str] = ..., version_id: _Optional[str] = ...) -> None: ...

class DeleteObjectResponse(_message.Message):
    __slots__ = ("success", "message", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    error: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class DeleteObjectsRequest(_message.Message):
    __slots__ = ("bucket_name", "user_id", "object_keys", "quiet")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEYS_FIELD_NUMBER: _ClassVar[int]
    QUIET_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    user_id: str
    object_keys: _containers.RepeatedScalarFieldContainer[str]
    quiet: bool
    def __init__(self, bucket_name: _Optional[str] = ..., user_id: _Optional[str] = ..., object_keys: _Optional[_Iterable[str]] = ..., quiet: bool = ...) -> None: ...

class DeleteObjectsResponse(_message.Message):
    __slots__ = ("success", "deleted_keys", "errors", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    DELETED_KEYS_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    deleted_keys: _containers.RepeatedScalarFieldContainer[str]
    errors: _containers.RepeatedCompositeFieldContainer[DeleteError]
    error: str
    def __init__(self, success: bool = ..., deleted_keys: _Optional[_Iterable[str]] = ..., errors: _Optional[_Iterable[_Union[DeleteError, _Mapping]]] = ..., error: _Optional[str] = ...) -> None: ...

class DeleteError(_message.Message):
    __slots__ = ("key", "error_code", "error_message")
    KEY_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    key: str
    error_code: str
    error_message: str
    def __init__(self, key: _Optional[str] = ..., error_code: _Optional[str] = ..., error_message: _Optional[str] = ...) -> None: ...

class ListObjectsRequest(_message.Message):
    __slots__ = ("bucket_name", "user_id", "prefix", "delimiter", "max_keys", "start_after", "continuation_token", "recursive")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    PREFIX_FIELD_NUMBER: _ClassVar[int]
    DELIMITER_FIELD_NUMBER: _ClassVar[int]
    MAX_KEYS_FIELD_NUMBER: _ClassVar[int]
    START_AFTER_FIELD_NUMBER: _ClassVar[int]
    CONTINUATION_TOKEN_FIELD_NUMBER: _ClassVar[int]
    RECURSIVE_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    user_id: str
    prefix: str
    delimiter: str
    max_keys: int
    start_after: str
    continuation_token: str
    recursive: bool
    def __init__(self, bucket_name: _Optional[str] = ..., user_id: _Optional[str] = ..., prefix: _Optional[str] = ..., delimiter: _Optional[str] = ..., max_keys: _Optional[int] = ..., start_after: _Optional[str] = ..., continuation_token: _Optional[str] = ..., recursive: bool = ...) -> None: ...

class ListObjectsResponse(_message.Message):
    __slots__ = ("success", "objects", "common_prefixes", "next_continuation_token", "is_truncated", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    OBJECTS_FIELD_NUMBER: _ClassVar[int]
    COMMON_PREFIXES_FIELD_NUMBER: _ClassVar[int]
    NEXT_CONTINUATION_TOKEN_FIELD_NUMBER: _ClassVar[int]
    IS_TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    objects: _containers.RepeatedCompositeFieldContainer[ObjectInfo]
    common_prefixes: _containers.RepeatedScalarFieldContainer[str]
    next_continuation_token: str
    is_truncated: bool
    error: str
    def __init__(self, success: bool = ..., objects: _Optional[_Iterable[_Union[ObjectInfo, _Mapping]]] = ..., common_prefixes: _Optional[_Iterable[str]] = ..., next_continuation_token: _Optional[str] = ..., is_truncated: bool = ..., error: _Optional[str] = ...) -> None: ...

class CopyObjectRequest(_message.Message):
    __slots__ = ("source_bucket", "source_key", "dest_bucket", "dest_key", "user_id", "metadata", "metadata_directive")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SOURCE_BUCKET_FIELD_NUMBER: _ClassVar[int]
    SOURCE_KEY_FIELD_NUMBER: _ClassVar[int]
    DEST_BUCKET_FIELD_NUMBER: _ClassVar[int]
    DEST_KEY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    METADATA_DIRECTIVE_FIELD_NUMBER: _ClassVar[int]
    source_bucket: str
    source_key: str
    dest_bucket: str
    dest_key: str
    user_id: str
    metadata: _containers.ScalarMap[str, str]
    metadata_directive: str
    def __init__(self, source_bucket: _Optional[str] = ..., source_key: _Optional[str] = ..., dest_bucket: _Optional[str] = ..., dest_key: _Optional[str] = ..., user_id: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ..., metadata_directive: _Optional[str] = ...) -> None: ...

class CopyObjectResponse(_message.Message):
    __slots__ = ("success", "message", "etag", "last_modified", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ETAG_FIELD_NUMBER: _ClassVar[int]
    LAST_MODIFIED_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    etag: str
    last_modified: _timestamp_pb2.Timestamp
    error: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., etag: _Optional[str] = ..., last_modified: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class StatObjectRequest(_message.Message):
    __slots__ = ("bucket_name", "object_key", "user_id", "version_id")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_ID_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_key: str
    user_id: str
    version_id: str
    def __init__(self, bucket_name: _Optional[str] = ..., object_key: _Optional[str] = ..., user_id: _Optional[str] = ..., version_id: _Optional[str] = ...) -> None: ...

class StatObjectResponse(_message.Message):
    __slots__ = ("success", "object_info", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    OBJECT_INFO_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    object_info: ObjectInfo
    error: str
    def __init__(self, success: bool = ..., object_info: _Optional[_Union[ObjectInfo, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class GetPresignedURLRequest(_message.Message):
    __slots__ = ("bucket_name", "object_key", "user_id", "expiry_seconds", "request_params")
    class RequestParamsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    EXPIRY_SECONDS_FIELD_NUMBER: _ClassVar[int]
    REQUEST_PARAMS_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_key: str
    user_id: str
    expiry_seconds: int
    request_params: _containers.ScalarMap[str, str]
    def __init__(self, bucket_name: _Optional[str] = ..., object_key: _Optional[str] = ..., user_id: _Optional[str] = ..., expiry_seconds: _Optional[int] = ..., request_params: _Optional[_Mapping[str, str]] = ...) -> None: ...

class GetPresignedURLResponse(_message.Message):
    __slots__ = ("success", "url", "expires_at", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    url: str
    expires_at: _timestamp_pb2.Timestamp
    error: str
    def __init__(self, success: bool = ..., url: _Optional[str] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class GetPresignedPutURLRequest(_message.Message):
    __slots__ = ("bucket_name", "object_key", "user_id", "expiry_seconds", "content_type")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    EXPIRY_SECONDS_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_key: str
    user_id: str
    expiry_seconds: int
    content_type: str
    def __init__(self, bucket_name: _Optional[str] = ..., object_key: _Optional[str] = ..., user_id: _Optional[str] = ..., expiry_seconds: _Optional[int] = ..., content_type: _Optional[str] = ...) -> None: ...

class GetPresignedPutURLResponse(_message.Message):
    __slots__ = ("success", "url", "expires_at", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    url: str
    expires_at: _timestamp_pb2.Timestamp
    error: str
    def __init__(self, success: bool = ..., url: _Optional[str] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class InitiateMultipartUploadRequest(_message.Message):
    __slots__ = ("bucket_name", "object_key", "user_id", "content_type", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_key: str
    user_id: str
    content_type: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, bucket_name: _Optional[str] = ..., object_key: _Optional[str] = ..., user_id: _Optional[str] = ..., content_type: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class InitiateMultipartUploadResponse(_message.Message):
    __slots__ = ("success", "upload_id", "bucket_name", "object_key", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_ID_FIELD_NUMBER: _ClassVar[int]
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    upload_id: str
    bucket_name: str
    object_key: str
    error: str
    def __init__(self, success: bool = ..., upload_id: _Optional[str] = ..., bucket_name: _Optional[str] = ..., object_key: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class UploadPartRequest(_message.Message):
    __slots__ = ("metadata", "chunk")
    METADATA_FIELD_NUMBER: _ClassVar[int]
    CHUNK_FIELD_NUMBER: _ClassVar[int]
    metadata: UploadPartMetadata
    chunk: bytes
    def __init__(self, metadata: _Optional[_Union[UploadPartMetadata, _Mapping]] = ..., chunk: _Optional[bytes] = ...) -> None: ...

class UploadPartMetadata(_message.Message):
    __slots__ = ("bucket_name", "object_key", "user_id", "upload_id", "part_number", "part_size")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_ID_FIELD_NUMBER: _ClassVar[int]
    PART_NUMBER_FIELD_NUMBER: _ClassVar[int]
    PART_SIZE_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_key: str
    user_id: str
    upload_id: str
    part_number: int
    part_size: int
    def __init__(self, bucket_name: _Optional[str] = ..., object_key: _Optional[str] = ..., user_id: _Optional[str] = ..., upload_id: _Optional[str] = ..., part_number: _Optional[int] = ..., part_size: _Optional[int] = ...) -> None: ...

class UploadPartResponse(_message.Message):
    __slots__ = ("success", "part_number", "etag", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    PART_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ETAG_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    part_number: int
    etag: str
    error: str
    def __init__(self, success: bool = ..., part_number: _Optional[int] = ..., etag: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class CompletedPart(_message.Message):
    __slots__ = ("part_number", "etag")
    PART_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ETAG_FIELD_NUMBER: _ClassVar[int]
    part_number: int
    etag: str
    def __init__(self, part_number: _Optional[int] = ..., etag: _Optional[str] = ...) -> None: ...

class CompleteMultipartUploadRequest(_message.Message):
    __slots__ = ("bucket_name", "object_key", "user_id", "upload_id", "parts")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_ID_FIELD_NUMBER: _ClassVar[int]
    PARTS_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_key: str
    user_id: str
    upload_id: str
    parts: _containers.RepeatedCompositeFieldContainer[CompletedPart]
    def __init__(self, bucket_name: _Optional[str] = ..., object_key: _Optional[str] = ..., user_id: _Optional[str] = ..., upload_id: _Optional[str] = ..., parts: _Optional[_Iterable[_Union[CompletedPart, _Mapping]]] = ...) -> None: ...

class CompleteMultipartUploadResponse(_message.Message):
    __slots__ = ("success", "object_key", "etag", "location", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    ETAG_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    object_key: str
    etag: str
    location: str
    error: str
    def __init__(self, success: bool = ..., object_key: _Optional[str] = ..., etag: _Optional[str] = ..., location: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class AbortMultipartUploadRequest(_message.Message):
    __slots__ = ("bucket_name", "object_key", "user_id", "upload_id")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KEY_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_ID_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_key: str
    user_id: str
    upload_id: str
    def __init__(self, bucket_name: _Optional[str] = ..., object_key: _Optional[str] = ..., user_id: _Optional[str] = ..., upload_id: _Optional[str] = ...) -> None: ...

class AbortMultipartUploadResponse(_message.Message):
    __slots__ = ("success", "message", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    error: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ("detailed",)
    DETAILED_FIELD_NUMBER: _ClassVar[int]
    detailed: bool
    def __init__(self, detailed: bool = ...) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("success", "healthy", "status", "timestamp", "details", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    healthy: bool
    status: str
    timestamp: _timestamp_pb2.Timestamp
    details: _struct_pb2.Struct
    error: str
    def __init__(self, success: bool = ..., healthy: bool = ..., status: _Optional[str] = ..., timestamp: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., details: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...
