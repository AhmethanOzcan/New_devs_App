from typing import Dict, Any, List

async def get_tenant_properties(tenant_id: str) -> List[Dict[str, Any]]:
    """
    Lists the properties that belong to a single tenant.
    """
    from app.core.database_pool import db_pool
    from sqlalchemy import text

    await db_pool.initialize()

    if not db_pool.session_factory:
        raise Exception("Database pool not available")

    async with db_pool.get_session() as session:
        query = text("""
            SELECT id, name, timezone
            FROM properties
            WHERE tenant_id = :tenant_id
            ORDER BY id
        """)

        result = await session.execute(query, {"tenant_id": tenant_id})

        return [
            {"id": row.id, "name": row.name, "timezone": row.timezone}
            for row in result.fetchall()
        ]
