from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from nexus.modules.database import database
import logging
import re

logger = logging.getLogger("nexus.db_explorer")

router = APIRouter(prefix="/api/admin/db", tags=["db_explorer"])

# --- Schemas ---

class TableInfo(BaseModel):
    name: str
    schema: str
    type: str

class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool
    default: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    parameters: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int

class SessionSearchResponse(BaseModel):
    tables: List[Dict[str, Any]]

# --- Helper Functions ---

def validate_select_query(query: str) -> bool:
    """
    Validates that the query is a SELECT-only query.
    Prevents SQL injection by disallowing DML/DDL keywords.
    """
    query_upper = query.strip().upper()
    
    # Must start with SELECT
    if not query_upper.startswith("SELECT"):
        return False
    
    # Disallow dangerous keywords
    dangerous_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", 
        "TRUNCATE", "EXECUTE", "EXEC", "CREATE", "GRANT",
        "REVOKE", "COMMIT", "ROLLBACK", "SAVEPOINT"
    ]
    
    for keyword in dangerous_keywords:
        # Check if keyword appears as a standalone word (not part of another word)
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, query_upper):
            return False
    
    return True

# --- Endpoints ---

@router.get("/tables", response_model=List[TableInfo])
async def list_tables():
    """
    Returns list of all tables in the database.
    Queries PostgreSQL information_schema.tables.
    """
    try:
        query = """
        SELECT table_name as name, table_schema as schema, table_type as type
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
        """
        rows = await database.fetch_all(query)
        return [TableInfo(**dict(row)) for row in rows]
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")

@router.get("/tables/{table_name}/schema", response_model=List[ColumnInfo])
async def get_table_schema(table_name: str):
    """
    Returns column information for a specific table.
    Queries information_schema.columns.
    """
    try:
        # Validate table name to prevent injection (basic check)
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        query = """
        SELECT 
            column_name as name,
            data_type as type,
            is_nullable = 'YES' as nullable,
            column_default as default
        FROM information_schema.columns
        WHERE table_name = :table_name
          AND table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY ordinal_position
        """
        rows = await database.fetch_all(query, {"table_name": table_name})
        
        if not rows:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        result = []
        for row in rows:
            result.append(ColumnInfo(
                name=row["name"],
                type=row["type"],
                nullable=row["nullable"],
                default=row["default"]
            ))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table schema for {table_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get table schema: {str(e)}")

@router.post("/query", response_model=QueryResponse)
async def execute_query(
    req: QueryRequest,
    x_user_id: str = Header("unknown", alias="X-User-ID")
):
    """
    Executes a SELECT query against the database.
    Validates that the query is SELECT-only and uses parameterized queries.
    """
    try:
        # Validate query
        if not validate_select_query(req.query):
            raise HTTPException(
                status_code=400, 
                detail="Only SELECT queries are allowed. DML/DDL keywords are not permitted."
            )
        
        # Execute query with parameters
        parameters = req.parameters or {}
        rows = await database.fetch_all(req.query, parameters)
        
        if not rows:
            return QueryResponse(columns=[], rows=[], row_count=0)
        
        # Extract column names from first row
        columns = list(rows[0].keys())
        
        # Convert rows to dictionaries
        row_dicts = [dict(row) for row in rows]
        
        return QueryResponse(
            columns=columns,
            rows=row_dicts,
            row_count=len(row_dicts)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

@router.get("/session/{session_id}")
async def search_session(session_id: int):
    """
    Finds all tables that have a session_id column and returns entries matching the session_id.
    """
    try:
        # Find all tables with session_id column
        query = """
        SELECT DISTINCT table_name
        FROM information_schema.columns
        WHERE column_name = 'session_id'
          AND table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_name
        """
        table_rows = await database.fetch_all(query)
        
        if not table_rows:
            return SessionSearchResponse(tables=[])
        
        results = []
        
        for table_row in table_rows:
            table_name = table_row["table_name"]
            
            try:
                # Query each table for matching session_id
                # Use parameterized query with table name (validate first)
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
                    logger.warning(f"Skipping table with invalid name: {table_name}")
                    continue
                
                select_query = f'SELECT * FROM "{table_name}" WHERE session_id = :session_id LIMIT 1000'
                rows = await database.fetch_all(select_query, {"session_id": session_id})
                
                if rows:
                    # Convert rows to dictionaries
                    row_dicts = [dict(row) for row in rows]
                    results.append({
                        "table_name": table_name,
                        "row_count": len(row_dicts),
                        "rows": row_dicts
                    })
            except Exception as e:
                logger.warning(f"Error querying table {table_name} for session_id {session_id}: {e}")
                # Continue with other tables even if one fails
                continue
        
        return SessionSearchResponse(tables=results)
    except Exception as e:
        logger.error(f"Error searching for session_id {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Session search failed: {str(e)}")



