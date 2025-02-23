from typing import Any, Dict, List, Tuple
import os
from dotenv import load_dotenv
import json
from jsonschema import validate, ValidationError
import google.generativeai as genai
from couchbase.cluster import Cluster, ClusterOptions, QueryOptions
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions, ClusterTimeoutOptions, SearchOptions
import couchbase.search as search
from couchbase.vector_search import VectorQuery, VectorSearch
from datetime import timedelta

load_dotenv(dotenv_path="config/.env")


# text to data for search filter(using google gen AI)
def text_to_json(text: str, json_schema: dict) -> Dict[str, Any]:
    model = genai.GenerativeModel("gemini-1.5-flash")
    json_str = json.dumps(json_schema, indent=3)

    response = model.generate_content(
        f"Translate the text to English and fill in the JSON values. Only fill the title if explicitly mentioned. Don't add new values, just ignore irrelevant words. If the text requests specific story or genre, set overview. If the text requests humor, set minimum_rating to 8.0; if a 'rating' number is mentioned, set minimum_rating to that number (maximum number is 9.5); otherwise, set it to 0.0. Return only the JSON, no comments: {text}{json_str}",
        generation_config=genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=100,
            temperature=0.2,
        ),
    )  
    response = response.text.strip()
    response = response.replace("json", "")
    response = response.replace("```", "")
    response_json = json.loads(response)
    response_json["year_range"] = response_json.get("year_range", [1900, 2025])
    response_json["overview"] = response_json.get("overview", text) # overview키가 존재하지 않을 시, text넣고 만듦
    if response_json.get("overview") == '': # overview키는 존재하나 값이 empty일 때
        response_json["overview"] = text
    response_json["minimum_rating"] = response_json.get("minimum_rating", 0.0)
    return response_json


def create_filter(
    year_range: Tuple[int], rating: float, search_in_title: bool, title: str
) -> Dict[str, Any]:
    """Create a filter for the hybrid search"""
    # Fields in the document used for search
    year_field = "Released_Year"
    rating_field = "IMDB_Rating"
    title_field = "Series_Title"

    filter = {}
    filter_operations = []
    if year_range:
        year_query = {
            "min": year_range[0],
            "max": year_range[1],
            "inclusive_min": True,
            "inclusive_max": True,
            "field": year_field,
        }
        filter_operations.append(year_query)
    if rating:
        filter_operations.append(
            {
                "min": rating,
                "inclusive_min": False,
                "field": rating_field,
            }
        )
    if search_in_title:
        filter_operations.append(
            {
                "match_phrase": title,
                "field": title_field,
            }
        )
    filter["query"] = {"conjuncts": filter_operations}
    return filter



def generate_embeddings(input_data):
    """Google Generative AI를 사용하여 입력 데이터의 임베딩을 생성합니다"""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=input_data,
        task_type="retrieval_query",
    )
    return result['embedding']


def connect_to_couchbase(connection_string, db_username, db_password):
    timeout_opt = ClusterTimeoutOptions(
        kv_timeout=timedelta(seconds=20),
        query_timeout=timedelta(seconds=20),
        search_timeout=timedelta(seconds=20),
        connect_timeout=timedelta(seconds=20),
    )
    
    options = ClusterOptions(
        PasswordAuthenticator(db_username, db_password),
        timeout_options=timeout_opt
    )

    connect_string = connection_string
    cluster = Cluster(connect_string, options)

    # Wait until the cluster is ready for use.
    cluster.wait_until_ready(timedelta(seconds=10))

    return cluster



def search_couchbase(
    db_scope: Any,
    index_name: str,
    embedding_key: str,
    search_text: str,
    k: int = 5,
    fields: List[str] = ["*"],
    search_options: Dict[str, Any] = {},
):
    """Hybrid search using Python SDK in couchbase"""
    # Generate vector embeddings to search with
    search_embedding = generate_embeddings(search_text)

    # Create the search request
    search_req = search.SearchRequest.create(
        VectorSearch.from_vector_query(
            VectorQuery(
                embedding_key,
                search_embedding,
                k,
            )
        )
    )

    docs_with_score = []

    try:
        # Perform the search
        search_iter = db_scope.search(
            index_name,
            search_req,
            SearchOptions(
                limit=k,
                fields=fields,
                raw=search_options,
            ),
        )

        # Parse the results
        for row in search_iter.rows():
            score = row.score
            docs_with_score.append((row.fields, score))
    except Exception as e:
        raise e

    return docs_with_score




genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Load environment variables
DB_CONN_STR = os.getenv("DB_CONN_STR")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_BUCKET = os.getenv("DB_BUCKET")
DB_SCOPE = os.getenv("DB_SCOPE")
DB_COLLECTION = os.getenv("DB_COLLECTION")
INDEX_NAME = os.getenv("INDEX_NAME")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")






def searchMovie(text):

    initial_movie_json = {
	"title": "",
    "overview": "",
    "director": "",
	"year_range": [1900, 2025],
	"minimum_rating": 0.0
    }
    response_json = text_to_json(text, initial_movie_json)

    # filters
    search_filters = {}
    search_filters = create_filter(year_range=(response_json["year_range"]), rating=response_json["minimum_rating"], search_in_title = False, title=text)


    # Connect to Couchbase Vector Store
    cluster = connect_to_couchbase(DB_CONN_STR, DB_USERNAME, DB_PASSWORD)
    bucket = cluster.bucket(DB_BUCKET)
    scope = bucket.scope(DB_SCOPE)

    no_of_results = 10
    search_text = response_json["overview"]

    try:
        results = search_couchbase(
                scope,
                INDEX_NAME,
                "Overview_embedding",
                search_text,                    # overview
                k=no_of_results,
                search_options=search_filters
            )
        
        if results is None:
            raise ValueError("Null value from movie search")
        
        return results
    
    except Exception as e:
        return "Null value"
        
    # return json.dumps(results)
    