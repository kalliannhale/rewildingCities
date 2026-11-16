# canopy/terraform ~ the canonical stack

One Terraform stack (infrastructure D-3, D-306) for the canonical bucket that
Contract 2 describes: field-guide/docs/contracts/02-canonical-objects.md.

## What it makes

| Piece | File | What it does |
| --- | --- | --- |
| The canonical bucket | bucket.tf | Private, versioned, TLS-only, SSE-S3 with SSE-C blocked, Block Public Access declared on, noncurrent versions kept (D-307) |
| The overwrite lock | bucket.tf | The bucket policy refuses a put to `harvests/*/versions/*` without If-None-Match, and a put to `harvests/*/current` without If-None-Match or If-Match (D-309). No copies into harvests/ |
| Public reach | cloudfront.tf | CloudFront with origin access control reads `harvests/*` only; versions cache long, `current` never; any origin may GET (D-302, D-310) |
| The writer | writer.tf | The role `rewilding-canonical-writer`: put, get and list under harvests/, every delete denied, no access key (D-308) |
| Access logs | access_logging.tf | S3 access logs into CloudWatch Logs, KMS-encrypted, 90 days |
| The budget | budget.tf | Only when `create_budget` is true (D-311) |

## Variables

| Variable | Default | Notes |
| --- | --- | --- |
| `aws_region` | `us-east-1` | D-301; an account that builds elsewhere sets its own |
| `environment_name` | `production` | A name component of every resource |
| `create_budget` | `true` | False where the account already has a budget |
| `budget_name` | `rewilding-monthly` | |
| `monthly_budget_limit_usd` | `50` | Alerts at 25, 50, 80 and 100 percent, and a forecast at 100 |
| `budget_alert_email_addresses` | `[]` | The budget refuses to plan without one |
| `access_log_retention_days` | `90` | |
| `cloudfront_price_class` | `PriceClass_100` | North America and Europe |

An account's own values go in a local `<name>.auto.tfvars` file beside the
stack, which Terraform reads by itself and `.gitignore` keeps out of the
public repo (`**/*.tfvars`). An email address or anything else private goes
there too, never in a committed file.

## Who runs it, and the state

The deployer is a person's own AWS login. State is local and ignored
(`*.tfstate`, `*.tfstate.backup`, `.terraform/`), kept on the machine of the
one person who applies. The provider lock, `.terraform.lock.hcl`, is committed.

## The order

1. `terraform init`, then `terraform validate`.
2. `terraform plan`, read before anything is applied: the bucket's name ends in
   `-<account>-<region>-an` exactly once, and nothing is to be destroyed.
3. Where `create_budget` is true, apply the budget first:
   `terraform apply -target=aws_budgets_budget.monthly`.
4. `terraform apply`.
5. The acceptance reads, as the writer: a put under harvests/ succeeds; the
   file reads through CloudFront with `access-control-allow-origin: *`; a put
   to a version without If-None-Match is refused; with it, it succeeds once
   and is refused the second time; a delete is refused.

## The writer's profile

The canonical write assumes the writer role through a profile in
`~/.aws/config`, its `role_arn` taken from the `canonical_writer_role_arn`
output:

```
[profile rewilding-writer]
role_arn = <canonical_writer_role_arn>
source_profile = <the deployer's profile>
region = <the stack's region>
```

## Kalli's configuration, November 2026 (the handover addendum)

The stack was tested and run on Kalli's own AWS account and is handed to the
Northeastern University Library as code (D-301).

- The account was made through AWS's new sign-up experience: a project inside
  an organization AWS set up for it, with service control policies Kalli does
  not edit. One keeps the account in the US East regions; another refuses S3
  buckets and KMS tagging in us-east-1. So Kalli's copy runs in us-east-2, the
  project's assigned region, set in her local `.auto.tfvars`. An account made
  through the advanced sign-up has no such policies and keeps the default.
- The account keeps a budget made in the AWS console, so `create_budget` is
  false there. The library sets it true and gives an alert address, or keeps
  a budget of its own and sets it false.
- The deployer was an IAM user with AdministratorAccess and an access key,
  retired after delivery (DEPLOY-1). The library should deploy from IAM
  Identity Center logins, which expire on their own.
- The acceptance reads' two small files stay under `harvests/_read/`.
