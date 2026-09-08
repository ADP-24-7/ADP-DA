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
| Explicit bucket allowlist | `ADP_NCP_ALLOWED_ARTIFACT_BUCKETS` |

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

The configured artifact bucket must also be present in the explicit allowlist. Bucket names
containing `tfstate` are always rejected, so a DA artifact cannot be written to the Terraform
State bucket even when the environment is configured incorrectly.

Object keys are immutable in both implementations:

- missing key + valid bytes: create
- existing key + identical bytes: idempotent success
- existing key + different bytes: fail with `ArtifactIntegrityError`

NCP writes are downloaded immediately and SHA-256 verified. If a later manifest operation
fails, objects newly created by that publish attempt are deleted best-effort; replayed objects
are never deleted by rollback.

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

## Two manifest layers

The generic **Storage Object Manifest** and the BE **Digital Asset Artifact Bundle Manifest**
have different responsibilities and are not interchangeable.

| Layer | Responsibility | Consumer |
|---|---|---|
| Storage Object Manifest `1.0.0` | One object's bucket/key/byte digest/size/provenance | DA storage tooling |
| Digital Asset Bundle `adp-digital-asset-artifact-bundle/v1` | Canonical contract, institution/workload binding and five required artifact roles | BE P0-5 Loader |

The final BE handoff always points to the Digital Asset Bundle Manifest and has exactly these
request fields:

```json
{
  "manifestReference": "handoff/validated/<artifact>/<version>/manifest.json",
  "expectedContentDigest": "sha256:<canonical-manifest-content-digest>"
}
```

`storageManifestDigest` is retained in the local reference file only so DA can verify the raw
manifest bytes downloaded from NCP. It is not sent as `expectedContentDigest`.

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

To retain secret-free completion evidence, execute the module after loading the ignored env:

```bash
set -a; source .env.ncp.local; set +a
ADP_CODE_GIT_SHA="$(git rev-parse HEAD)" \
ADP_NCP_STORAGE_E2E_CONFIRM=YES \
python -m adp_da.ncp_storage_e2e --execute \
  --evidence-output 02_ai/artifacts/ncp_storage/NCP_STORAGE_E2E.json
```

The evidence records the adapter Git SHA, bucket, upload/download digest match and cleanup
result. It never records credential values.

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

The reference file contains no credential. This generic Storage Object reference is useful
for a single artifact, but it is **not** a BE P0-5 ingest request.

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

## Publish the BE P0-5 Digital Asset Bundle

The copied `be_loader_v1` schemas are byte-frozen against the BE feature branch. The publisher
validates all five domain documents, canonicalizes JSON exactly as BE does, publishes the five
files and the domain manifest, then reads every object back and verifies its SHA-256 digest.

```bash
set -a; source .env.ncp.local; set +a
export ADP_NCP_DIGITAL_ASSET_BUNDLE_PUBLISH_CONFIRM=YES
export ADP_CODE_GIT_SHA="$(git rev-parse HEAD)"

python -m adp_da.digital_asset_bundle_cli \
  --source-dir 03_digital_asset/artifacts/be_loader_v1 \
  --schema-dir 03_digital_asset/contracts/be_loader_v1 \
  --artifact-id DA-DIGITAL-ASSET-RUNTIME-CANDIDATE-001 \
  --artifact-version 1.0.0 \
  --institution-id institution_local \
  --destination-profile-id dest_mock_asset_platform_v1 \
  --reference-output 03_digital_asset/artifacts/be_loader_v1/ncp-ingest-reference.json
```

Independently download and validate the persisted manifest and all five files:

```bash
python -m adp_da.digital_asset_bundle_verify_cli \
  --reference 03_digital_asset/artifacts/be_loader_v1/ncp-ingest-reference.json \
  --schema-dir 03_digital_asset/contracts/be_loader_v1 \
  --evidence-output 03_digital_asset/artifacts/be_loader_v1/ncp-verify-evidence.json
```

The reference's `manifestReference` and `expectedContentDigest` are the BE API request values.
At the time of this DA change, the compared BE feature branch has only a local ContentStore.
Therefore NCP publication and BE-contract validation are complete on DA, while a real BE API
ingest from the NCP key requires the BE NCP ContentStore/configuration to be merged and running.

## Failure policy

- Credential or confirmation missing: reject before creating the client
- Non-NCP or non-HTTPS endpoint: reject before sending credentials
- Invalid object key: reject before storage access
- Terraform State or non-allowlisted bucket: reject before storage access
- Missing object: raise `ArtifactNotFoundError`
- Timeout/SDK error: raise `ArtifactStorageError` without credential details
- Digest, manifest, bucket or size mismatch: raise `ArtifactIntegrityError`

Troubleshooting discovered during a real integration run belongs in
`02_ai/docs/troubleshooting/ncp-object-storage.md` with secrets redacted.
