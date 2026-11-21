"""Map Oracle and PowerCenter column types to DuckDB types."""

TEXT = {"varchar2", "varchar", "nvarchar2", "char", "nchar", "string", "nstring", "text", "ntext", "clob"}
INTEGER = {"integer", "int", "small integer", "smallint"}
FLOAT = {"double", "float", "real", "binary_double", "binary_float"}
DATETIME = {"date", "timestamp", "date/time"}


class UnsupportedType(Exception):
    pass


def duck_type(datatype: str, precision: int, scale: int) -> str:
    d = datatype.lower()
    if d in TEXT:
        return "varchar"
    if d in ("number(p,s)", "decimal", "numeric"):
        return f"decimal({precision},{scale})"
    if d == "number":
        return f"decimal({precision},{scale})" if precision else "double"
    if d in INTEGER:
        return "integer"
    if d == "bigint":
        return "bigint"
    if d in FLOAT:
        return "double"
    if d in DATETIME:
        return "timestamp"  # an Oracle DATE also holds a time of day
    raise UnsupportedType(datatype)


def scale_of(datatype: str, scale: int):
    """Decimal places a value of this type can carry: None means unlimited (floating point)."""
    d = datatype.lower()
    if d in FLOAT:
        return None
    if d in INTEGER or d == "bigint":
        return 0
    if d in ("number(p,s)", "decimal", "numeric", "number"):
        return scale
    return -1  # not a number
