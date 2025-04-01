from dotenv import load_dotenv
from fastapi import FastAPI, Query, Depends
from typing import Dict, List, Any, Optional
import uvicorn
from pydantic import BaseModel

from datetime import datetime
import uuid

from supabase_client import supabase
import os
load_dotenv()


app = FastAPI(title="Product Search API")

# Pydantic models for response validation
class Attributes(BaseModel):
    brand: str
    size: str
    weight: float

class Product(BaseModel):
    id: str
    name: str
    description: str
    category: str
    tags: List[str]
    attributes: Attributes

class Coordinates(BaseModel):
    x: float
    y: float

class Location(BaseModel):
    product_id: str
    store_id: str
    aisle: str
    section: str
    shelf: str
    coordinates: Coordinates

class Store(BaseModel):
    id: str
    name: str
    address: str
    layout: Dict[str, Any]

class ProductWithLocation(BaseModel):
    product: Product
    location: Optional[Location] = None
    store: Optional[Store] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None

class SearchQuery(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    brand: Optional[str] = None
    store_id: Optional[str] = None
    min_weight: Optional[float] = None
    max_weight: Optional[float] = None
    
class Ingredient(BaseModel):
    recipe_id: str
    product_id: str
    quantity: float
    unit: str

class Recipe(BaseModel):
    id: str
    name: str
    description: str
    ingredients: Optional[List[Ingredient]] = None

class RecipeWithDetails(BaseModel):
    recipe: Recipe
    ingredients_details: Optional[List[ProductWithLocation]] = None # Include product details for each ingredient

class SearchLog(BaseModel):
    id: Optional[str] = None
    search_type: str  # "product" o "recipe"
    query_term: str
    found: bool
    timestamp: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None

# Helper function to get data source
def get_data_source(): return supabase

@app.get("/")
def read_root():
    return {"message": "Welcome to the Product Search API", "data_source": "Supabase"}

# Add this helper function to transform Supabase data to match your models
def transform_supabase_data(data_type, data):
    """Transform Supabase data to match Pydantic models structure."""
    if data_type == "product":
        # Check if the data has attributes nested or flattened
        if "attributes" not in data:
            # Create attributes object from flattened fields
            return {
                "id": data["id"],
                "name": data["name"],
                "description": data["description"],
                "category": data["category"],
                "tags": data["tags"],
                "attributes": {
                    "brand": data.get("brand", ""),
                    "size": data.get("size", ""),
                    "weight": float(data.get("weight", 0))
                }
            }
        return data
    
    elif data_type == "location":
        # Check if coordinates are nested or flattened
        if "coordinates" not in data:
            return {
                "product_id": data["product_id"],
                "store_id": data["store_id"],
                "aisle": data["aisle"],
                "section": data["section"],
                "shelf": data["shelf"],
                "coordinates": {
                    "x": float(data.get("x_coordinate", 0)),
                    "y": float(data.get("y_coordinate", 0))
                }
            }
        return data
    
    elif data_type == "store":
        # Check if layout is nested or flattened
        if "layout" not in data:
            return {
                "id": data["id"],
                "name": data["name"],
                "address": data["address"],
                "layout": {
                    "aisles": int(data.get("aisles", 0)),
                    "sections": int(data.get("sections", 0))
                }
            }
        return data
    
    return data

# Simplify the transformation function
def transform_data(data, data_type):
    """Transform data based on type to ensure compatibility with Pydantic models."""
    if not data:
        return None
        
    if data_type == "product" and "attributes" not in data:
        data["attributes"] = {
            "brand": data.pop("brand", ""),
            "size": data.pop("size", ""),
            "weight": float(data.pop("weight", 0))
        }
    elif data_type == "location" and "coordinates" not in data:
        data["coordinates"] = {
            "x": float(data.pop("x_coordinate", 0)),
            "y": float(data.pop("y_coordinate", 0))
        }
    elif data_type == "store" and "layout" not in data:
        data["layout"] = {
            "aisles": int(data.pop("aisles", 0)),
            "sections": int(data.pop("sections", 0))
        }
    # Handle recipe data transformation
    elif data_type == "recipe":
            
        # Ensure all required fields are present
        if "id" not in data:
            data["id"] = ""
        if "name" not in data:
            data["name"] = ""
        if "description" not in data:
            data["description"] = ""
        if "ingredients" not in data:
            data["ingredients"] = []
    
    return data

# Unified function to get data
def get_data(table, filters=None, data_source=get_data_source()):
    """Get data from Supabase with optional filters."""
    if data_source is None:
        return []   

    query = data_source.table(table).select("*")
    
    if filters:
        for key, value in filters.items():
            if key == "ilike":
                for field, term in value.items():
                    query = query.ilike(field, f"%{term}%")
            elif key == "eq":
                for field, term in value.items():
                    query = query.eq(field, term)
            elif key == "contains":
                for field, terms in value.items():
                    for term in terms:
                        query = query.contains(field, [term])
    
    response = query.execute()
    return response.data

@app.get("/products/", response_model=List[Product])
def get_products(
    name: Optional[str] = Query(None, description="Filter by product name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag")
):
    """
    Search for products with optional filters for name, category, and tags.
    """
    filters = {}
    
    if name:
        filters["ilike"] = {"name": name}
    
    if category:
        filters["eq"] = {"category": category}
    
    if tag:
        filters["contains"] = {"tags": [tag]}
    
    products = get_data("products", filters)
    
    # Search log
    search_term = name or category or tag or "all"
    found = len(products) > 0
    log_search("product", search_term, found, {
        "filters": filters,
        "results_count": len(products)
    })
    
    return [transform_data(p, "product") for p in products]

@app.get("/products/{product_id}", response_model=ProductWithLocation)
def get_product(product_id: str, include_location: bool = True, include_store: bool = True):
    """
    Get detailed information about a specific product.
    Optionally include location and store information.
    """
    products = get_data("products", {"eq": {"id": product_id}})
    
    if not products:
        return {"error": "Product not found"}
    
    product = transform_data(products[0], "product")
    result = {"product": product}
    
    if include_location:
        locations = get_data("locations", {"eq": {"product_id": product_id}})
        
        if locations:
            location = transform_data(locations[0], "location")
            result["location"] = location
            
            if include_store and location:
                stores = get_data("stores", {"eq": {"id": location["store_id"]}})
                
                if stores:
                    store = transform_data(stores[0], "store")
                    result["store"] = store
    
    return result

@app.get("/stores/{store_id}/products", response_model=List[ProductWithLocation])
def get_store_products(store_id: str, data_source = get_data_source()):
    """
    Get all products available in a specific store with their locations.
    """
    # Get locations for the store
    locations_response = data_source.table("locations").select("*").eq("store_id", store_id).execute()
    store_locations = locations_response.data
    
    results = []
    for location in store_locations:
        product_response = data_source.table("products").select("*").eq("id", location["product_id"]).execute()
        product = product_response.data[0] if product_response.data else None
        
        if product:
            results.append({
                "product": product,
                "location": location
            })

    return results

@app.post("/search/", response_model=List[ProductWithLocation])
def search_products(query: SearchQuery):
    """
    Advanced search endpoint that allows searching with multiple criteria.
    Returns products with their locations and store information when available.
    """
    filters = {}
    
    if query.name:
        filters["ilike"] = filters.get("ilike", {})
        filters["ilike"]["name"] = query.name
        
    if query.category:
        filters["eq"] = filters.get("eq", {})
        filters["eq"]["category"] = query.category
        
    if query.tags:
        filters["contains"] = filters.get("contains", {})
        filters["contains"]["tags"] = query.tags
        
    # Get filtered products
    products = get_data("products", filters)
    
    # Further filter by attributes that might require special logic
    if query.brand or query.min_weight is not None or query.max_weight is not None:
        filtered_products = []
        for product in products:
            p = transform_data(product, "product")

            if not p:
                continue    
            
            if query.brand and p["attributes"]["brand"].lower() != query.brand.lower():
                continue
                
            if query.min_weight is not None and p["attributes"]["weight"] < query.min_weight:
                continue
                
            if query.max_weight is not None and p["attributes"]["weight"] > query.max_weight:
                continue
                
            filtered_products.append(product)
        products = filtered_products
    
    # Advanced search log
    search_term = query.name or query.category or (query.tags[0] if query.tags else None) or query.brand or "advanced_search"
    found = len(products) > 0
    log_search("product_advanced", search_term, found, {
        "filters": filters,
        "query_params": query.dict(exclude_none=True),
        "results_count": len(products)
    })
    
    # Build results with location and store
    results = []
    for product in products:
        transformed_product = transform_data(product, "product")
        
        # Find location for this product
        locations = get_data("locations", {"eq": {"product_id": product["id"]}})
        location = locations[0] if locations else None
        
        # Skip if store_id is specified and doesn't match
        if query.store_id and (not location or location["store_id"] != query.store_id):
            continue
            
        transformed_location = transform_data(location, "location") if location else None
        
        # Find store for this location
        store = None
        if location:
            stores = get_data("stores", {"eq": {"id": location["store_id"]}})
            store = stores[0] if stores else None
        
        transformed_store = transform_data(store, "store") if store else None
        
        # Add to results
        results.append({
            "product": transformed_product,
            "location": transformed_location,
            "store": transformed_store
        })
    
    return results

@app.post("/search_recipes/", response_model=List[RecipeWithDetails])
def search_recipes(query: SearchQuery):
    """
    Advanced search endpoint for recipes.
    Allows searching by recipe name and ingredient.
    Returns recipes with detailed ingredient information including product locations.
    Uses efficient database search for large datasets.
    """
    filters = {}
    
    if query.name:
        # For Supabase, use multiple ilike conditions to implement fuzzy search
        search_term = query.name.lower().strip()
        search_words = search_term.split()
        
        # Get recipes with any word match using Supabase's built-in search
        recipes = []
        # First try exact match with ilike
        exact_filters = {"ilike": {"name": search_term}}
        exact_matches = get_data("recipes", exact_filters)
        recipes.extend(exact_matches)
        
        # Then try word-by-word matches
        for word in search_words:
            if len(word) > 2:  # Skip very short words
                word_filters = {"ilike": {"name": word}}
                word_matches = get_data("recipes", word_filters)
                # Add only new matches
                for match in word_matches:
                    if not any(r["id"] == match["id"] for r in recipes):
                        recipes.append(match)
                            
    else:
        return []
    
    # Log della ricerca avanzata di ricette
    search_term = query.name or "advanced_recipe_search"
    found = len(recipes) > 0
    log_search("recipe_advanced", search_term, found, {
        "filters": filters,
        "query_params": query.dict(exclude_none=True),
        "results_count": len(recipes)
    })
    
    # Build results with ingredient details
    results = []
    for recipe in recipes:
        transformed_recipe = transform_data(recipe, "recipe")

        recipe_ingredients = get_data("recipe_ingredients", {"eq": {"recipe_id": recipe["id"]}})

        # Get product details for each ingredient
        ingredients_details = []
        if len(recipe_ingredients) > 0:
            for ingredients in recipe_ingredients:
                product_id = ingredients["product_id"]
                
                # Get product info
                products = get_data("products", {"eq": {"id": product_id}})
                if products:
                    product = transform_data(products[0], "product")
                    
                    # Get location info
                    locations = get_data("locations", {"eq": {"product_id": product_id}})
                    location = transform_data(locations[0], "location") if locations else None
                    
                    # Get store info if location exists
                    store = None
                    if location:
                        stores = get_data("stores", {"eq": {"id": location["store_id"]}})
                        store = transform_data(stores[0], "store") if stores else None
                    
                    # Add complete product info to ingredients
                    ingredients_details.append({
                        "product": product,
                        "location": location,
                        "store": store,
                        "quantity": ingredients.get("quantity", 0),
                        "unit": ingredients.get("unit", "")
                    })
        
        results.append({
            "recipe": transformed_recipe,
            "ingredients_details": ingredients_details
        })
    
    return results

@app.get("/recipes/", response_model=List[Recipe])
def get_recipes(
    name: Optional[str] = Query(None, description="Filter by recipe name")
):
    """
    Get all recipes with optional name filter
    """
    filters = {}
    if name:
        filters["ilike"] = {"name": name}
    
    recipes = get_data("recipes", filters)
    
    # Log della ricerca
    search_term = name or "all"
    found = len(recipes) > 0
    log_search("recipe", search_term, found, {
        "filters": filters,
        "results_count": len(recipes)
    })
    
    return [transform_data(r, "recipe") for r in recipes]

@app.get("/recipes/{recipe_id}", response_model=RecipeWithDetails)
def get_recipe(recipe_id: str):
    """
    Get detailed information about a specific recipe including ingredient details with locations
    """
    recipes = get_data("recipes", {"eq": {"id": recipe_id}})

    if not recipes:
        return {"error": "Recipe not found"}
        
    recipe = recipes[0]
    transformed_recipe = transform_data(recipe, "recipe")

    recipe_ingredients = get_data("recipe_ingredients", {"eq": {"recipe_id": recipe["id"]}})

    # Get product details for each ingredient
    ingredients_details = []
    if len(recipe_ingredients) > 0:
        for ingredients in recipe_ingredients:
            product_id = ingredients["product_id"]
            
            # Get product info
            products = get_data("products", {"eq": {"id": product_id}})
            if products:
                product = transform_data(products[0], "product")
                
                # Get location info
                locations = get_data("locations", {"eq": {"product_id": product_id}})
                location = transform_data(locations[0], "location") if locations else None
                
                # Get store info if location exists
                store = None
                if location:
                    stores = get_data("stores", {"eq": {"id": location["store_id"]}})
                    store = transform_data(stores[0], "store") if stores else None
                
                # Add complete product info to ingredients
                ingredients_details.append({
                    "product": product,
                    "location": location,
                    "store": store,
                    "quantity": ingredients.get("quantity", 0),
                    "unit": ingredients.get("unit", "")
                })
    return {
        "recipe": transformed_recipe,
        "ingredients_details": ingredients_details
    }
    
@app.get("/recipes/by-ingredient/{product_id}", response_model=List[Recipe])
def get_recipes_by_ingredient(product_id: str):
    """
    Get all recipes that use a specific product as ingredient
    """
    recipes = get_data("recipes")
    
    matching_recipes = []
    for recipe in recipes:
        ingredients =  get_data("recipe_ingredients", {"eq": {"recipe_id": recipe["id"]}})
        if any(ing["product_id"] == product_id for ing in ingredients):
            matching_recipes.append(transform_data(recipe, "recipe"))
            
    return matching_recipes

@app.post("/recipes/best-by-ingredients", response_model=Recipe)
def get_best_recipe_by_ingredients(ingredient_ids: List[str] = Query(..., description="List of ingredient IDs")):
    """
    Get the best recipe that contains the highest number of specified ingredients.
    
    Args:
        ingredient_ids: List of product IDs representing the ingredients.
        
    Returns:
        The recipe that contains the highest number of specified ingredients.
    """
    recipes = get_data("recipes")
    best_recipe = None
    max_matching = 0

    for recipe in recipes:
        ingredients = get_data("recipe_ingredients", {"eq": {"recipe_id": recipe["id"]}})
        matching_count = sum(1 for ing in ingredients if ing["product_id"] in ingredient_ids)
        
        if matching_count > max_matching:
            max_matching = matching_count
            best_recipe = recipe

    if not best_recipe:
        return {"error": "No matching recipe found"}

    return best_recipe

def log_search(search_type: str, query_term: str, found: bool, details: Optional[Dict[str, Any]] = None):
    """
    Log a search in the logging database.
    
    Args:
        search_type: Type of search ("product" or "recipe")
        query_term: Search term used
        found: Whether the item was found
        details: Optional additional details about the search
    """
    log_entry = {
        "id": str(uuid.uuid4()),
        "search_type": search_type,
        "query_term": query_term,
        "found": found,
        "timestamp": datetime.now().isoformat(),
        "details": details or {}
    }

    # Insert the log in Supabase
    supabase.table("search_logs").insert(log_entry).execute()
    
    return log_entry

@app.get("/logs/", response_model=List[SearchLog])
def get_logs(
    search_type: Optional[str] = Query(None, description="Filter by search type (product/recipe)"),
    found: Optional[bool] = Query(None, description="Filter by found status"),
    limit: int = Query(100, description="Maximum number of logs to return")
):
    """
    Retrieve search logs with optional filters.
    """
    filters = {}
    
    if search_type:
        filters["eq"] = filters.get("eq", {})
        filters["eq"]["search_type"] = search_type
        
    if found is not None:
        filters["eq"] = filters.get("eq", {})
        filters["eq"]["found"] = found
    
    logs = get_data("search_logs", filters)
    
    # Ordina per timestamp (più recenti prima)
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Limita il numero di risultati
    logs = logs[:limit]
    
    return logs


@app.get("/logs/stats")
def get_logs_stats():
    """
    Get aggregated statistics from search logs.
    """
    logs = get_data("search_logs")
    
    if not logs:
        return {
            "total_searches": 0,
            "successful_searches": 0,
            "failed_searches": 0,
            "search_types": {},
            "top_products": [],
            "top_not_found": [],
            "daily_stats": {}
        }
    
    # Statistiche generali
    total_searches = len(logs)
    successful_searches = len([log for log in logs if log["found"]])
    failed_searches = total_searches - successful_searches
    
    # Conteggio per tipo di ricerca
    search_types = {}
    for log in logs:
        search_type = log["search_type"]
        if search_type not in search_types:
            search_types[search_type] = 0
        search_types[search_type] += 1
    
    # Top prodotti ricercati
    product_searches = [log for log in logs if log["search_type"] in ["product", "product_advanced"]]
    product_terms = {}
    for log in product_searches:
        term = log["query_term"]
        if term in ["all", "advanced_search"]:
            continue
        if term not in product_terms:
            product_terms[term] = {"total": 0, "found": 0}
        product_terms[term]["total"] += 1
        if log["found"]:
            product_terms[term]["found"] += 1
    
    top_products = [
        {
            "term": term,
            "count": stats["total"],
            "found_percent": (stats["found"] / stats["total"]) * 100
        }
        for term, stats in product_terms.items()
    ]
    top_products.sort(key=lambda x: x["count"], reverse=True)
    top_products = top_products[:10]  # Top 10
    
    # Top prodotti non trovati
    not_found_searches = [log for log in product_searches if not log["found"]]
    not_found_terms = {}
    for log in not_found_searches:
        term = log["query_term"]
        if term in ["all", "advanced_search"]:
            continue
        if term not in not_found_terms:
            not_found_terms[term] = 0
        not_found_terms[term] += 1
    
    top_not_found = [
        {"term": term, "count": count}
        for term, count in not_found_terms.items()
    ]
    top_not_found.sort(key=lambda x: x["count"], reverse=True)
    top_not_found = top_not_found[:10]  # Top 10
    
    # Statistiche giornaliere
    daily_stats = {}
    for log in logs:
        # Estrai la data dalla timestamp
        if isinstance(log["timestamp"], str):
            date = log["timestamp"].split("T")[0]
        else:
            date = log["timestamp"].strftime("%Y-%m-%d")
            
        if date not in daily_stats:
            daily_stats[date] = {"total": 0, "success": 0, "failed": 0}
        daily_stats[date]["total"] += 1
        if log["found"]:
            daily_stats[date]["success"] += 1
        else:
            daily_stats[date]["failed"] += 1
    
    return {
        "total_searches": total_searches,
        "successful_searches": successful_searches,
        "failed_searches": failed_searches,
        "search_types": search_types,
        "top_products": top_products,
        "top_not_found": top_not_found,
        "daily_stats": daily_stats
    }


if __name__ == "__main__":

    uvicorn.run("product_api:app", host="0.0.0.0", port=int(os.environ.get("DB_PORT", 8100)), reload=True)

