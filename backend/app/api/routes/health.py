from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    Used by frontend and monitoring to verify the API is running.
    """
    return {
        "status": "ok",
        "service": "NDA Chatbot API"
    }
