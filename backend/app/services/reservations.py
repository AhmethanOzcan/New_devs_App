from decimal import Decimal
from typing import Dict, Any, List

async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int) -> Dict[str, Any]:
    """
    Calculates revenue for a specific month.

    Month boundaries are evaluated in the property's own timezone, so a booking
    checking in at 2024-02-29 23:30 UTC (00:30 on March 1st in Paris) counts
    towards March for a Paris property.
    """
    from app.core.database_pool import db_pool
    from sqlalchemy import text

    await db_pool.initialize()

    if not db_pool.session_factory:
        raise Exception("Database pool not available")

    async with db_pool.get_session() as session:
        # make_timestamp() builds local midnight; AT TIME ZONE converts it to the
        # matching UTC instant for that property's timezone.
        query = text("""
            SELECT
                COALESCE(SUM(r.total_amount), 0) as total_revenue,
                COUNT(r.id) as reservation_count
            FROM reservations r
            JOIN properties p
                ON p.id = r.property_id AND p.tenant_id = r.tenant_id
            WHERE r.property_id = :property_id
            AND r.tenant_id = :tenant_id
            AND r.check_in_date >= (make_timestamp(:year, :month, 1, 0, 0, 0) AT TIME ZONE p.timezone)
            AND r.check_in_date < ((make_timestamp(:year, :month, 1, 0, 0, 0) + interval '1 month') AT TIME ZONE p.timezone)
        """)

        result = await session.execute(query, {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "month": month,
            "year": year
        })
        row = result.fetchone()

        return {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "total": str(Decimal(str(row.total_revenue))),
            "currency": "USD",
            "count": row.reservation_count
        }

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    try:
        # Use the shared database pool (initialized once, reused across requests)
        from app.core.database_pool import db_pool

        await db_pool.initialize()
        
        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                # Use SQLAlchemy text for raw SQL
                from sqlalchemy import text
                
                query = text("""
                    SELECT 
                        property_id,
                        SUM(total_amount) as total_revenue,
                        COUNT(*) as reservation_count
                    FROM reservations 
                    WHERE property_id = :property_id AND tenant_id = :tenant_id
                    GROUP BY property_id
                """)
                
                result = await session.execute(query, {
                    "property_id": property_id, 
                    "tenant_id": tenant_id
                })
                row = result.fetchone()
                
                if row:
                    total_revenue = Decimal(str(row.total_revenue))
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": str(total_revenue),
                        "currency": "USD", 
                        "count": row.reservation_count
                    }
                else:
                    # No reservations found for this property
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": "0.00",
                        "currency": "USD",
                        "count": 0
                    }
        else:
            raise Exception("Database pool not available")
            
    except Exception as e:
        print(f"Database error for {property_id} (tenant: {tenant_id}): {e}")

        # Never serve fabricated figures for financial data - surface the failure instead
        raise
