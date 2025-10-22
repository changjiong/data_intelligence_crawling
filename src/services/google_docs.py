from __future__ import annotations

import logging
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as AuthRequest

from storage.models import Attachment, Policy

logger = logging.getLogger(__name__)

DOCS_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]


@dataclass
class ExportResult:
    document_id: str
    document_url: str
    attachments: Iterable[Attachment]


def _load_credentials(scopes: Optional[Iterable[str]] = None):
    scopes = list(scopes or DOCS_SCOPES)
    oauth_secret_file = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_FILE")
    if oauth_secret_file:
        return _load_oauth_credentials(oauth_secret_file, scopes=scopes)

    credentials_info = os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO")
    credentials_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if credentials_info:
        import json

        data = json.loads(credentials_info)
        return service_account.Credentials.from_service_account_info(data, scopes=scopes)
    if credentials_file:
        path = Path(credentials_file).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Service account file not found: {path}")
        return service_account.Credentials.from_service_account_file(str(path), scopes=scopes)
    raise RuntimeError(
        "Missing Google credentials. Provide GOOGLE_OAUTH_CLIENT_SECRET_FILE or service account variables."
    )


def _load_oauth_credentials(secret_path: str, scopes: Iterable[str]) -> UserCredentials:
    secret_file = Path(secret_path).expanduser()
    if not secret_file.exists():
        raise FileNotFoundError(f"OAuth client secret file not found: {secret_file}")

    token_path = Path(os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "credentials/token.json")).expanduser()
    if token_path.exists():
        creds = UserCredentials.from_authorized_user_file(str(token_path), scopes=scopes)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(AuthRequest())
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json())
            return creds

    flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), scopes=scopes)
    print("\n[Google OAuth] 打开授权 URL 完成登录（首次运行需要授权）...")
    creds = flow.run_local_server(
        open_browser=True,
        authorization_prompt_message="复制上方链接到浏览器以授权，如果未自动打开。",
        success_message="授权成功，可以返回终端。",
    )
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    return creds


class GoogleDocsExporter:
    """Helper that exports policies to Google Docs and uploads attachments to Drive."""

    def __init__(self, credentials=None, folder_id: str | None = None) -> None:
        self.credentials = credentials or _load_credentials()
        self.folder_id = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        self._docs_service = build("docs", "v1", credentials=self.credentials, cache_discovery=False)
        self._drive_service = build("drive", "v3", credentials=self.credentials, cache_discovery=False)

    def export(self, policy: Policy) -> ExportResult:
        document = self._docs_service.documents().create(body={"title": self._document_title(policy)}).execute()
        doc_id = document["documentId"]
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

        body_text = self._compose_body(policy)
        self._docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": body_text}}]},
        ).execute()

        uploaded_attachments = list(self._upload_attachments(policy.attachments))
        if uploaded_attachments:
            attachment_text = "\n附件：\n" + "\n".join(
                f"- {att.name}: {att.drive_view_url or att.drive_download_url or att.url}"
                for att in uploaded_attachments
            )
            self._docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1 + len(body_text)}, "text": attachment_text}}]},
            ).execute()

        if self.folder_id:
            self._move_doc_to_folder(doc_id)

        policy.google_doc_id = doc_id
        policy.google_doc_url = doc_url
        policy.attachments = uploaded_attachments

        return ExportResult(document_id=doc_id, document_url=doc_url, attachments=uploaded_attachments)

    def _compose_body(self, policy: Policy) -> str:
        parts = [
            policy.title,
            f"发布日期：{policy.publish_date.isoformat() if policy.publish_date else '未知'}",
            f"来源：{policy.site or '中小科创'}",
            f"原始链接：{policy.source_url}",
            "",
            policy.content_text or "",
        ]
        return "\n".join(parts).strip() + "\n"

    def _document_title(self, policy: Policy) -> str:
        prefix = f"{policy.publish_date.isoformat()} " if policy.publish_date else ""
        title = f"{prefix}{policy.title}"
        return title[:300]

    def _upload_attachments(self, attachments: Iterable[Attachment]) -> Iterable[Attachment]:
        for attachment in attachments:
            if not attachment.local_path:
                logger.info("Skip uploading attachment without local_path: %s", attachment.name)
                continue
            path = Path(attachment.local_path)
            if not path.exists():
                logger.warning("Attachment file not found for upload: %s", path)
                continue
            mime_type = attachment.mime_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            metadata = {"name": path.name}
            if self.folder_id:
                metadata["parents"] = [self.folder_id]
            media = MediaFileUpload(str(path), mimetype=mime_type, resumable=False)
            response = self._drive_service.files().create(body=metadata, media_body=media, fields="id, webViewLink, webContentLink").execute()
            attachment.mime_type = mime_type
            attachment.drive_file_id = response.get("id")
            attachment.drive_view_url = response.get("webViewLink")
            attachment.drive_download_url = response.get("webContentLink")
            logger.info("Uploaded attachment %s to Drive file %s", attachment.name, attachment.drive_file_id)
            yield attachment

    def _move_doc_to_folder(self, doc_id: str) -> None:
        try:
            existing = self._drive_service.files().get(fileId=doc_id, fields="parents").execute()
            previous_parents = ",".join(existing.get("parents", []))
            request_kwargs = {
                "fileId": doc_id,
                "addParents": self.folder_id,
                "fields": "id, parents",
            }
            if previous_parents:
                request_kwargs["removeParents"] = previous_parents
            self._drive_service.files().update(**request_kwargs).execute()
        except HttpError as exc:
            logger.warning("Failed to move doc %s into folder %s: %s", doc_id, self.folder_id, exc)
