from typing import List, Dict, Optional

from google.oauth2 import service_account
from google.cloud import bigquery

from .models import CategoryType
from .enums import *


BASE_QUERY = f"""
SELECT 
item.*, 
FROM `{PROJECT_ID}.{DATASET_ID}.{ITEM_ACTIVE_TABLE_ID}` item
LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.{PINECONE_TABLE_ID}` AS p ON item.id = p.item_id
LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.{SOLD_TABLE_ID}` AS s USING (vinted_id)
WHERE p.item_id IS NULL AND s.vinted_id IS NULL
"""


def init_client(credentials_dict: Dict) -> bigquery.Client:
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict
    )

    return bigquery.Client(
        credentials=credentials, project=credentials_dict["project_id"]
    )


def load_items_to_embed(
    client: bigquery.Client,
    shuffle: bool = False,
    n: Optional[int] = None,
    category_type: Optional[CategoryType] = None,
) -> bigquery.table.RowIterator:
    query = _query_items_to_embed(
        shuffle=shuffle,
        n=n,
        category_type=category_type,
    )

    print(query)

    return client.query(query).result()


def upload(client: bigquery.Client, table_id: str, rows: List[Dict]) -> bool:
    try:
        if len(rows) == 0:
            return False

        errors = client.insert_rows_json(
            table=f"{PROJECT_ID}.{DATASET_ID}.{table_id}", json_rows=rows
        )

        if not errors:
            return True
        else:
            print(errors)
            return False

    except Exception as e:
        print(e)
        return False


def delete(client: bigquery.Client, table_id: str, conditions: List[str]) -> bool:
    query = f"""
    DELETE FROM `{PROJECT_ID}.{DATASET_ID}.{table_id}`
    WHERE {conditions}
    """

    try:
        client.query(query).result()
        return True
    except Exception as e:
        print(e)
        return False


def _query_items_to_embed(
    shuffle: bool = False,
    n: Optional[int] = None,
    category_type: Optional[CategoryType] = None,
) -> str:
    query = BASE_QUERY

    if category_type is not None:
        query += f" AND category_type = '{category_type}'"
    else:
        category_types = ", ".join(
            [f"'{category_type}'" for category_type in CATEGORY_TYPES]
        )
        query += f" AND category_type IN ({category_types})"

    if shuffle:
        query += "\nORDER BY RAND()"
    else:
        query += "\nORDER BY created_at DESC"

    if n is not None:
        query += f"\nLIMIT {n}"

    return query
