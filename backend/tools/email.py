"""LangChain tools for Gmail integration via Google API."""
from langchain_core.tools import tool

from backend.services import email_service


@tool
def list_emails(max_results: int = 10, label: str = "INBOX") -> str:
    """List recent emails from a Gmail label. Returns sender, subject, snippet, and message ID."""
    try:
        results = email_service.list_emails(max_results, label)
        return str(results)
    except Exception as e:
        return f"Error accessing Gmail: {str(e)}. Please ensure credentials are configured."


@tool
def get_email(message_id: str) -> str:
    """Get the full content of an email by its message ID."""
    try:
        result = email_service.get_email(message_id)
        return str(result)
    except Exception as e:
        return f"Error retrieving email: {str(e)}"


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient."""
    try:
        return email_service.send_email(to, subject, body)
    except Exception as e:
        return f"Error sending email: {str(e)}"


@tool
def search_emails(query: str, max_results: int = 10) -> str:
    """Search emails using Gmail search syntax (e.g., 'from:boss@company.com is:unread')."""
    try:
        results = email_service.search_emails(query, max_results)
        return str(results)
    except Exception as e:
        return f"Error searching emails: {str(e)}"
