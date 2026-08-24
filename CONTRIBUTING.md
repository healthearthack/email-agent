# Contributing to email-agent

Thank you for contributing to `email-agent`.

This repository contains an email automation agent that reads eligible inbound Gmail messages, filters automated or notification traffic, generates a response with Gemini, optionally synchronizes contact data with HubSpot and Salesforce, renders a multipart plain-text and HTML email, and places the result in Gmail Drafts for human review before sending.

The project intentionally uses a human-in-the-loop safety boundary: contributors must preserve draft-only behavior unless a change explicitly proposes, documents, and receives review for a different delivery model.

## Acronyms used in this document

- **AI** — Artificial Intelligence
- **API** — Application Programming Interface
- **CRM** — Customer Relationship Management
- **HITL** — Human-in-the-Loop
- **HTML** — Hypertext Markup Language
- **IMAP** — Internet Message Access Protocol
- **OAuth** — Open Authorization
- **PR** — Pull Request
- **SMTP** — Simple Mail Transfer Protocol
- **YAML** — YAML Ain't Markup Language

## Repository workflow

The current production-style flow is:

```text
Gmail Inbox
     |
     v
Inbound Message Discovery
     |
     v
Automated / Notification Filter
     |
     v
Eligible Human Message
     |
     v
Optional CRM Synchronization
     |
     v
Gemini Response Generation
     |
     v
Markdown + HTML Rendering
     |
     v
Gmail Draft
     |
     v
Human Review
     |
     v
Human-Authorized Send
```

The scheduled GitHub Actions workflow is located at:

```text
.github/workflows/gmail-ai-draft-agent.yml
```

The primary scheduled entry point is currently:

```text
metaknews@gmail.com.py
```

A second implementation also exists at:

```text
email-agent.py
```

Contributors should identify which implementation their change affects and avoid unintentionally creating inconsistent behavior between the two files.

## Before opening a Pull Request

Complete every applicable item below before submitting a Pull Request.

### Repository and branch checks

- [ ] I created my work on a dedicated branch rather than committing directly to `main`.
- [ ] My branch is based on the latest intended base branch.
- [ ] My commits are limited to the change described by this Pull Request.
- [ ] I reviewed `git diff` before committing.
- [ ] I removed temporary files, debug output, generated credentials, test secrets, and unrelated edits.
- [ ] I used clear commit messages that explain what changed.
- [ ] I confirmed the repository still contains no committed `.env` file, application password, access token, client secret, security token, or private credential.

### Python checks

- [ ] The edited Python files parse successfully.
- [ ] Imports required by the changed code are present in the GitHub Actions dependency installation step or otherwise documented.
- [ ] Environment variables are read with `os.getenv(...)` or another approved runtime configuration mechanism rather than hard-coded credentials.
- [ ] Exceptions contain enough information to diagnose failures without exposing secret values.
- [ ] Retry logic, where used, is bounded and cannot create an uncontrolled loop.
- [ ] Network calls use reasonable timeouts where supported.
- [ ] New behavior does not silently swallow failures that should cause the GitHub Actions run to fail.

A minimum local syntax check is:

```bash
python -m py_compile email-agent.py
python -m py_compile "metaknews@gmail.com.py"
```

### Gmail and message-processing checks

- [ ] The change does not expose `GMAIL_APP_PASSWORD` or another Gmail credential in source code, logs, screenshots, test fixtures, or Pull Request text.
- [ ] The change preserves correct Gmail authentication behavior.
- [ ] The change preserves or improves automated-message filtering.
- [ ] The agent continues to ignore messages sent from its own configured mailbox.
- [ ] The agent does not reply to obvious no-reply, bulk, notification, billing, or automated traffic unless the Pull Request explicitly changes that policy.
- [ ] Sender parsing handles both display names and raw email addresses.
- [ ] Subject decoding remains safe for encoded message headers.
- [ ] Multipart email parsing does not treat attachments as normal message body text.
- [ ] Reply threading preserves the original message identifier through `In-Reply-To` and `References` when available.

### Human-in-the-Loop guardrail checks

- [ ] The default workflow continues to create a Gmail draft rather than automatically send a generated response.
- [ ] Human review remains required before an outbound message is sent.
- [ ] The Pull Request does not bypass the Gmail Drafts guardrail indirectly through a new code path.
- [ ] Any proposed automatic-send behavior is isolated, disabled by default, clearly documented, and called out prominently in the Pull Request description.
- [ ] The generated recipient, subject, body, and thread headers are reviewable before sending.

### Gemini Artificial Intelligence checks

- [ ] `GEMINI_API_KEY` remains an environment variable or GitHub Actions secret and is never committed.
- [ ] The Gemini model is configurable rather than unnecessarily hard-coded when configuration is appropriate.
- [ ] Model failures surface useful diagnostics.
- [ ] Temporary model-service failures use bounded retry behavior if retrying is appropriate.
- [ ] Prompts do not contain credentials or unnecessary private account data.
- [ ] Generated content remains subject to human review before transmission.
- [ ] Changes to the system prompt are explained in the Pull Request description.
- [ ] Prompt changes preserve the intended role and behavior of the email agent unless the Pull Request explicitly proposes a product change.

### HubSpot Customer Relationship Management checks

- [ ] HubSpot integration remains optional when `HUBSPOT_ACCESS_TOKEN` is not configured.
- [ ] The HubSpot access token is not committed, printed, or embedded in a request URL.
- [ ] Contact synchronization failures do not expose secret values.
- [ ] The Pull Request documents any new HubSpot contact properties that must exist in the portal.
- [ ] New HubSpot Application Programming Interface calls include appropriate authentication and request handling.
- [ ] The change does not unexpectedly block Gmail draft generation solely because HubSpot is unavailable unless that behavior is explicitly intended and documented.

### Salesforce Customer Relationship Management checks

- [ ] Salesforce client credentials, password, and security token remain runtime secrets.
- [ ] Salesforce Open Authorization behavior is not weakened by the change.
- [ ] Lead creation or update logic is documented when changed.
- [ ] Salesforce synchronization failures do not expose passwords, security tokens, client secrets, or access tokens.
- [ ] The change does not unexpectedly block Gmail draft generation solely because Salesforce is unavailable unless that behavior is explicitly intended and documented.
- [ ] New Salesforce fields or object assumptions are listed in the Pull Request description.

### Email rendering checks

- [ ] The generated message still includes a plain-text body.
- [ ] The generated message still includes a Hypertext Markup Language body when rich rendering is enabled.
- [ ] Markdown conversion does not remove the plain-text fallback.
- [ ] The rendered email remains readable if remote images or tracking pixels are blocked.
- [ ] Layout changes have been checked for reasonable readability on narrow and desktop email clients.
- [ ] User-controlled message content is not inserted into executable code or unsafe configuration.

### GitHub Actions checks

- [ ] The workflow file remains valid YAML.
- [ ] The workflow checks out the repository before running repository code.
- [ ] The configured Python version is compatible with the code and installed dependencies.
- [ ] Any new Python dependency is added to the dependency installation step or a dependency file used by the workflow.
- [ ] Required secrets are referenced through GitHub Actions secrets rather than literal values.
- [ ] The scheduled job remains bounded by an appropriate timeout.
- [ ] `RUN_ONCE` behavior is preserved for scheduled execution unless the Pull Request explicitly changes the execution model.
- [ ] The workflow can also be started manually through `workflow_dispatch` unless removal is an intentional documented change.
- [ ] I checked the latest GitHub Actions run associated with my branch or Pull Request when a remote run was available.

### Security and privacy checks

- [ ] No secret, password, token, private key, session cookie, or authentication header is included in the commit.
- [ ] No real private email body is added as a public test fixture without explicit authorization.
- [ ] Logs contain only the minimum information needed for diagnosis.
- [ ] Personally identifiable information is not collected or stored unless required for the documented feature.
- [ ] New external services are documented before user data is transmitted to them.
- [ ] The change follows least-privilege principles for account permissions and GitHub Actions permissions.
- [ ] The Pull Request does not weaken the existing automated-sender filter without explaining the security and spam implications.
- [ ] The Pull Request does not silently introduce automatic outbound sending.

### Documentation checks

- [ ] `README.md` is updated when installation, configuration, workflow, supported integrations, or operator behavior changes.
- [ ] `CONTRIBUTING.md` is updated if contributor requirements change.
- [ ] New environment variables are documented by name and purpose.
- [ ] New setup steps are reproducible from a clean clone.
- [ ] Documentation distinguishes required configuration from optional integration configuration.
- [ ] Examples use placeholder credentials rather than real credentials.

## Pull Request submission criteria

A Pull Request should be ready for review only when all applicable criteria below are satisfied.

- [ ] The Pull Request has a concise title describing the actual change.
- [ ] The description explains the problem being solved.
- [ ] The description explains the implementation approach.
- [ ] The description identifies the files or major components changed.
- [ ] The description lists any new environment variables, GitHub Actions secrets, HubSpot properties, Salesforce fields, or external dependencies.
- [ ] The description explains any change to Gmail filtering, message selection, draft creation, or sending behavior.
- [ ] The description explains any change to the Gemini system prompt or model selection.
- [ ] The description includes test evidence.
- [ ] The description identifies any known limitation or follow-up work.
- [ ] The Pull Request does not combine unrelated cleanup, feature development, and refactoring unless there is a strong reason to review them together.
- [ ] The branch is pushed to GitHub and the Pull Request targets the correct base branch.
- [ ] All merge conflicts are resolved.
- [ ] The final diff has been reviewed by the contributor after the last change.

## Recommended Pull Request template

Use the following structure in the Pull Request description:

```markdown
## Summary

Describe what this Pull Request changes.

## Why

Describe the problem, bug, security concern, or feature request being addressed.

## Implementation

Describe the important technical decisions.

## Validation

- [ ] Python syntax check passed
- [ ] Relevant Gmail behavior tested
- [ ] Gmail draft creation verified when applicable
- [ ] Automated sender filtering verified when applicable
- [ ] Gemini generation path verified when applicable
- [ ] HubSpot synchronization verified or confirmed unaffected
- [ ] Salesforce synchronization verified or confirmed unaffected
- [ ] GitHub Actions workflow verified or confirmed unaffected
- [ ] No credentials or secrets committed

## Configuration changes

List new or changed environment variables, GitHub Actions secrets, Customer Relationship Management fields, or setup requirements. Write `None` when there are no configuration changes.

## Safety impact

Explain whether the Pull Request changes message selection, Artificial Intelligence generation, data synchronization, draft creation, or sending behavior.

## Known limitations

List anything intentionally left unresolved. Write `None` when there are no known limitations.
```

## Suggested branch naming

Use a short descriptive branch name. Examples:

```text
fix/gmail-draft-threading
fix/gemini-retry-handling
feature/hubspot-contact-sync
docs/contributing-guide
security/automated-sender-filter
refactor/email-renderer
```

## Suggested commit messages

Examples:

```text
Fix Gmail draft reply threading
Add bounded Gemini retry handling
Document required GitHub Actions secrets
Harden automated sender filtering
Add HubSpot contact sync error handling
```

## Local validation commands

From the repository root, contributors can run:

```bash
python -m py_compile email-agent.py
python -m py_compile "metaknews@gmail.com.py"
```

If dependencies are installed in a virtual environment, activate that environment before running the application.

Never place real credentials directly in shell history examples, source files, screenshots, issue comments, or Pull Request descriptions.

## Reviewing a Pull Request

Reviewers should confirm the following before approval:

- [ ] The change matches the stated scope.
- [ ] The code is understandable enough to maintain.
- [ ] Security-sensitive configuration remains secret-backed.
- [ ] Gmail message filtering has not been accidentally weakened.
- [ ] Human review remains in the outbound email path.
- [ ] New dependencies are justified and installed by the workflow.
- [ ] Failure paths are handled deliberately.
- [ ] Customer Relationship Management integrations remain optional unless the project intentionally changes that contract.
- [ ] Documentation reflects operator-visible changes.
- [ ] Test evidence is credible and relevant to the changed behavior.
- [ ] The final GitHub Actions status is successful when the workflow applies to the change.

## Merge criteria

A Pull Request may be merged when:

- [ ] Required review is complete.
- [ ] Requested changes are resolved.
- [ ] Applicable validation checks pass.
- [ ] No unresolved merge conflicts remain.
- [ ] No secrets are present in the diff.
- [ ] The Human-in-the-Loop draft guardrail remains intact or an intentional change has been explicitly reviewed and approved.
- [ ] Documentation is current for the merged behavior.

## Reporting security-sensitive problems

Do not publish credentials, tokens, account recovery information, private email contents, or exploitable configuration details in a public issue.

When reporting a security problem, provide the smallest amount of sensitive information necessary and use a private reporting channel when the repository owner has one configured.

## License

Contributions are made under the repository's existing license. Review `LICENSE` before contributing.
