# NCP Object Storage Integration

## Scope

ADP-DA publishes dataset and evaluation artifacts to the private QA bucket through a
storage-neutral `ArtifactStore`. ADP-Infra remains the resource source of truth; DA owns
object keys, manifests, upload/download integrity and the reference handed to BE.

The NCP foundation is documented in the Notion [NCP 설정](https://app.notion.com/p/3cd9924eda6e804ba415cadc0af4fcc1?pvs=204)
page and ADP-Infra `docs/ncp-bootstrap.md`.

## Fixed QA connection contract

| Setting | Value |
|---|---|
| Endpoint | `https://kr.object.ncloudstorage.com` |
| Region | `KR` |
| Data/artifact bucket | `adp-qa-data-artifacts` |
| Access key env | `NCLOUD_ACCESS_KEY` |
| Secret key env | `NCLOUD_SECRET_KEY` |

Credentials must exist only in process environment or the ignored `.env.ncp.local` file.
Do not put them in `.env.example`, GitHub Actions, Docker images, logs, manifests or reports.

## Storage contract

`ArtifactStore` has two implementations:

- `LocalArtifactStore`: local contract development and tests
- `NcpObjectStorageStore`: NCP S3-compatible API, path-style addressing and SigV4

Only these prefixes are accepted:

- `datasets/raw`, `datasets/curated`, `datasets/published`
- `artifacts/evaluation`, `artifacts/validation`, `artifacts/policy`
- `handoff/validated`, `replay`
- `manifests/datasets`, `manifests/artifacts`

Absolute paths, `..`, backslashes, non-normalized paths and unknown prefixes fail before any
storage request. Uploads do not set a public ACL.

Every published artifact has a canonical JSON manifest containing:

- schema, artifact and version identity
- bucket and object key
- `sha256:<lowercase hex>` digest and byte size
- producing Git commit
- data classification and source IDs

`publish_artifact` calculates the digest before upload, reads the object back, uploads the
manifest and verifies that too. `load_published_artifact` verifies the manifest digest,
schema, bucket, object digest and byte size before returning bytes. Missing, oversized or
tampered objects fail closed.

The returned BE handoff reference contains only bucket/key/version/digest metadata, never
credentials or raw object content.

## Local setup

```bash
make ncp-storage-env
chmod 600 .env.ncp.local
```

Populate the ignored file with the QA-scoped Object Storage credential. The existing Infra
credential file can be used without copying secrets:

```bash
make ncp-storage-preflight NCP_ENV=../ADP-Infra/.env.terraform.local
```

The preflight performs no network call and prints only presence booleans.

### Team member setup

Cloning ADP-DA or ADP-Infra never provides a credential because every real local env file is
ignored. Each team member who needs QA storage access must receive their own NCP Sub Account
key, or an explicitly approved QA service credential, through the team's secret channel.

1. Run `make ncp-storage-env`.
2. Put `NCLOUD_ACCESS_KEY` and `NCLOUD_SECRET_KEY` in `.env.ncp.local`.
3. Keep mode `600` and confirm `git check-ignore .env.ncp.local` succeeds.
4. Run `make ncp-storage-preflight`; never paste actual values into an issue or PR.
5. Enable a write confirmation only for the exact command being executed.

Pulling ADP-Infra is optional for a DA-only contributor. If it is present and its ignored
credential file has already been configured, Make commands can use
`NCP_ENV=../ADP-Infra/.env.terraform.local` without copying the key.

## Explicit NCP integration drill

Set `ADP_NCP_STORAGE_E2E_CONFIRM=YES` only for an intentional run, then execute:

```bash
make ncp-storage-e2e NCP_ENV=.env.ncp.local
```

The drill uploads synthetic bytes under a unique `replay/ncp-storage-e2e/...` key, uploads
its manifest, downloads and verifies both, and deletes only those two exact keys in `finally`.
The default `make check` never contacts NCP and incurs no storage operation.

## Publish a validated artifact

Load the ignored DA credential into the current Git Bash or POSIX shell and explicitly confirm
the persistent publish operation:

```bash
set -a
source .env.ncp.local
set +a
export ADP_NCP_ARTIFACT_PUBLISH_CONFIRM=YES

python -m adp_da.artifact_storage_cli publish \
  --source 02_ai/artifacts/ai_handoff_vNext/validation/VAL-AI-CUSTOMER-SUPPORT-VNEXT.json \
  --prefix handoff/validated \
  --artifact-id VAL-AI-CUSTOMER-SUPPORT-VNEXT \
  --artifact-version vNext \
  --code-git-sha 7323830a83dd293d1fb75d336332fbdf1f72354c \
  --classification SYNTHETIC_OR_PSEUDONYMIZED \
  --content-type application/json \
  --reference-output 02_ai/artifacts/ncp_storage/VAL-AI-CUSTOMER-SUPPORT-VNEXT.reference.json
```

The reference file contains no credential. It binds the persistent artifact to the Bucket,
Manifest key, Manifest digest, artifact identity and artifact digest required by the BE loader.

Download and independently verify it with:

```bash
python -m adp_da.artifact_storage_cli download \
  --reference 02_ai/artifacts/ncp_storage/VAL-AI-CUSTOMER-SUPPORT-VNEXT.reference.json \
  --output /tmp/VAL-AI-CUSTOMER-SUPPORT-VNEXT.downloaded.json

cmp \
  02_ai/artifacts/ai_handoff_vNext/validation/VAL-AI-CUSTOMER-SUPPORT-VNEXT.json \
  /tmp/VAL-AI-CUSTOMER-SUPPORT-VNEXT.downloaded.json
```

Do not enable publish confirmation globally or in a committed env file. A persistent artifact
is not deleted by the E2E cleanup command; delete or replace one only through an explicitly
reviewed lifecycle operation.

## Failure policy

- Credential or confirmation missing: reject before creating the client
- Non-NCP or non-HTTPS endpoint: reject before sending credentials
- Invalid object key: reject before storage access
- Missing object: raise `ArtifactNotFoundError`
- Timeout/SDK error: raise `ArtifactStorageError` without credential details
- Digest, manifest, bucket or size mismatch: raise `ArtifactIntegrityError`

Troubleshooting discovered during a real integration run belongs in
`02_ai/docs/troubleshooting/ncp-object-storage.md` with secrets redacted.
