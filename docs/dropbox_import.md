# Dropbox ticket import

The Dropbox module lets a super administrator authorize a Dropbox account and
select a main import folder. Create a Dropbox scoped-access app with
`files.metadata.read`, `files.content.read`, and `account_info.read`, add the
callback URL shown by the browser (`/admin/modules/dropbox/oauth/callback`) to
the app's redirect URIs, then save and connect it from **Admin → Modules →
Dropbox Ticket Import**.

## Folder contract (version 1)

```text
/configured-main-folder/
  requester@example.com/
    Unique ticket subject/
      call.m4a
      note_shortsummary.md
      note_summary.md
      note_transcript.txt
```

Each direct child of the main folder must be a valid requester email. Each
direct child below that becomes one ticket, with its folder name as the subject.
The UTF-8 `_shortsummary` text becomes the initial description. Every supported
file (`.m4a`, `.txt`, `.md`, or `.markdown`) is downloaded through Dropbox's
authenticated API, validated by the standard attachment pipeline, and attached
to the ticket. A Dropbox folder ID is imported only once.

App secrets and OAuth refresh tokens are encrypted at rest. Dropbox credentials
are never returned by the CRUD API. All `/api/dropbox` endpoints and the admin
page require super-administrator access; interactive forms also use CSRF
protection. CRUD and sync endpoints are documented in Swagger UI at `/docs`.
