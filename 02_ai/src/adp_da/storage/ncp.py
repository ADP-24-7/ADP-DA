"""NCP Object Storage adapter using its S3-compatible API."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, cast
from urllib.parse import urlsplit

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from adp_da.storage.core import (
    MAX_ARTIFACT_BYTES,
    ArtifactNotFoundError,
    ArtifactStorageError,
    validate_object_key,
    verify_bytes,
)

DEFAULT_ENDPOINT = "https://kr.object.ncloudstorage.com"
DEFAULT_REGION = "KR"
DEFAULT_BUCKET = "adp-qa-data-artifacts"


def _required(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name, "")
    if not value.strip():
        raise ValueError(f"{name} is required")
    if "\r" in value or "\n" in value:
        raise ValueError(f"{name} must not contain line breaks")
    return value


def _validate_endpoint(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or not parsed.hostname.endswith(".object.ncloudstorage.com")
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("NCP Object Storage endpoint must be an NCP HTTPS origin")
    return endpoint.rstrip("/")


class NcpObjectStorageStore:
    def __init__(self, client: Any, *, bucket: str) -> None:
        if not bucket or "/" in bucket:
            raise ValueError("invalid NCP Object Storage bucket")
        self.client = client
        self.bucket = bucket

    @classmethod
    def from_env(cls, environment: Mapping[str, str] | None = None) -> NcpObjectStorageStore:
        values = os.environ if environment is None else environment
        access_key = _required(values, "NCLOUD_ACCESS_KEY")
        secret_key = _required(values, "NCLOUD_SECRET_KEY")
        endpoint = _validate_endpoint(
            values.get("ADP_NCP_OBJECT_STORAGE_ENDPOINT", DEFAULT_ENDPOINT)
        )
        region = values.get("NCLOUD_REGION", DEFAULT_REGION)
        bucket = values.get("ADP_NCP_ARTIFACT_BUCKET", DEFAULT_BUCKET)
        config = Config(
            signature_version="s3v4",
            connect_timeout=5,
            read_timeout=30,
            retries={"max_attempts": 3, "mode": "standard"},
            s3={"addressing_style": "path"},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        )
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=config,
        )
        return cls(client, bucket=bucket)

    def put(self, object_key: str, data: bytes, *, digest: str, content_type: str) -> None:
        key = validate_object_key(object_key)
        verify_bytes(data, digest, MAX_ARTIFACT_BYTES)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentLength=len(data),
                ContentType=content_type,
                Metadata={"sha256": digest.removeprefix("sha256:")},
            )
        except (BotoCoreError, ClientError) as error:
            raise ArtifactStorageError("NCP artifact upload failed") from error

    def get(
        self, object_key: str, *, expected_digest: str, max_bytes: int = MAX_ARTIFACT_BYTES
    ) -> bytes:
        key = validate_object_key(object_key)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"]
            try:
                data = cast(bytes, body.read(max_bytes + 1))
            finally:
                body.close()
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise ArtifactNotFoundError(f"artifact not found: {key}") from error
            raise ArtifactStorageError("NCP artifact download failed") from error
        except BotoCoreError as error:
            raise ArtifactStorageError("NCP artifact download failed") from error
        verify_bytes(data, expected_digest, max_bytes)
        return data

    def delete(self, object_key: str) -> None:
        key = validate_object_key(object_key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except (BotoCoreError, ClientError) as error:
            raise ArtifactStorageError("NCP artifact cleanup failed") from error
