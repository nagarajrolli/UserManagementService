from fastapi import Header, HTTPException, status

async def verify_api_key_header(x_api_key: str = Header(...)):
    """
    Reusable authentication dependency.
    Validates the incoming header securely before granting access.
    """
    # Replace with real database lookups or cryptographically secure token validation
    if x_api_key != "super-secret-production-token-string":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided API Token is invalid or expired."
        )
    return x_api_key
