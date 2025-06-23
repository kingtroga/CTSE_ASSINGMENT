# django_app/web/smart_assistant.py
# =============================================================================
# Smart Assistant with Gemini API Integration
# =============================================================================

import os
import json
import requests
import logging
from typing import Dict, List, Any, Optional
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.conf import settings
import re

# Configure logging
logger = logging.getLogger(__name__)

class SmartAssistant:
    """Smart Assistant using Gemini API for SQL generation and data analysis"""
    
    def __init__(self):
        self.gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in Django settings")
        
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        
        # Database schema context for the AI
        self.schema_context = self._build_schema_context()
        
        # System prompt for SQL generation
        self.system_prompt = self._build_system_prompt()
    
    def _build_schema_context(self) -> str:
        """Build schema context from your Django models"""
        return """
DATABASE SCHEMA:

1. PRODUCTS TABLE (products):
   - msku (VARCHAR, PRIMARY KEY) - Master SKU identifier
   - product_name (VARCHAR) - Product name
   - category (VARCHAR) - Product category
   - brand (VARCHAR) - Product brand
   - cost_price (DECIMAL) - Cost price
   - is_active (BOOLEAN) - Active status
   - created_at, updated_at (DATETIME)

2. WAREHOUSES TABLE (warehouses):
   - code (VARCHAR, PRIMARY KEY) - Warehouse code (TLCQ, BLR7, etc.)
   - name (VARCHAR) - Warehouse name
   - location (VARCHAR) - City/region
   - is_active (BOOLEAN) - Active status
   - created_at, updated_at (DATETIME)

3. INVENTORY TABLE (inventory):
   - product_id (FK to products.msku)
   - warehouse_id (FK to warehouses.code)
   - current_stock (INTEGER) - Current stock level
   - buffer_stock (INTEGER) - Buffer/safety stock
   - opening_stock (INTEGER) - Opening stock
   - reorder_level (INTEGER) - Reorder threshold
   - last_updated (DATETIME)

4. MARKETPLACES TABLE (marketplaces):
   - code (VARCHAR, PRIMARY KEY) - CSTE_AMAZON, CSTE_FK, CSTE_MEESHO, GL_FK, RUDRAV_MEESHO
   - name (VARCHAR) - Marketplace name
   - commission_rate (DECIMAL) - Commission percentage
   - is_active (BOOLEAN)

5. SKU_MAPPINGS TABLE (sku_mappings):
   - sku (VARCHAR) - Marketplace SKU
   - product_id (FK to products.msku) - Master product
   - marketplace_id (FK to marketplaces.code) - Sales channel
   - marketplace_price (DECIMAL) - Listed price
   - status (VARCHAR) - ACTIVE, INACTIVE, etc.
   - created_at, updated_at (DATETIME)

6. ORDERS TABLE (orders):
   - order_id (VARCHAR, PRIMARY KEY) - Unique order ID
   - order_type (VARCHAR) - INBOUND, OUTBOUND, TRANSFER, etc.
   - status (VARCHAR) - PENDING, CONFIRMED, SHIPPED, etc.
   - marketplace_id (FK) - Source marketplace
   - warehouse_id (FK) - Primary warehouse
   - total_amount (DECIMAL) - Order value
   - order_date (DATETIME)

7. ORDER_ITEMS TABLE (order_items):
   - order_id (FK to orders.order_id)
   - product_id (FK to products.msku)
   - quantity (INTEGER) - Ordered quantity
   - unit_price (DECIMAL) - Price per unit
   - line_total (DECIMAL) - Total for line
   - item_status (VARCHAR)

8. INVENTORY_MOVEMENTS TABLE (inventory_movements):
   - movement_id (VARCHAR, PRIMARY KEY)
   - movement_type (VARCHAR) - INBOUND, OUTBOUND, TRANSFER_IN, etc.
   - product_id (FK to products.msku)
   - warehouse_id (FK to warehouses.code)
   - quantity (INTEGER) - Movement quantity (+/-)
   - stock_before, stock_after (INTEGER)
   - movement_date (DATETIME)

9. COMBO_PRODUCTS TABLE (combo_products):
   - combo_sku (VARCHAR, PRIMARY KEY)
   - combo_name (VARCHAR)
   - marketplace_id (FK)
   - combo_price (DECIMAL)
   - is_active (BOOLEAN)

10. COMBO_PRODUCT_ITEMS TABLE (combo_product_items):
    - combo_product_id (FK to combo_products.combo_sku)
    - product_id (FK to products.msku)
    - quantity (INTEGER) - Quantity in combo
"""
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for SQL generation"""
        return f"""You are a smart warehouse management assistant that converts natural language queries into SQL.

{self.schema_context}

IMPORTANT RULES:
1. ONLY generate SELECT queries - no INSERT, UPDATE, DELETE, DROP, etc.
2. Always use proper JOINs to connect related tables
3. Use meaningful column aliases for better readability
4. Add appropriate WHERE clauses for filtering
5. Include ORDER BY for sorted results
6. Limit results to reasonable numbers (use LIMIT when appropriate)
7. Use aggregate functions (COUNT, SUM, AVG) for summary queries
8. Handle date filters using DATE() function or date ranges
9. For stock analysis, remember current_stock can be 0 or negative
10. For marketplace analysis, join with sku_mappings to connect products to marketplaces

COMMON QUERY PATTERNS:
- Stock levels: JOIN inventory with products and warehouses
- Sales analysis: JOIN orders with order_items, products, and marketplaces
- Product performance: Use order_items with aggregations
- Inventory movements: JOIN with products and warehouses
- Marketplace comparison: GROUP BY marketplace with aggregations

RESPONSE FORMAT:
Return ONLY valid SQL query, no explanations or markdown formatting.

Example user queries and expected SQL patterns:
- "Show me top 10 products by stock" → SELECT with JOIN and ORDER BY
- "Low stock items" → WHERE current_stock <= reorder_level
- "Sales by marketplace" → JOIN orders with marketplaces, GROUP BY
- "Inventory movements today" → WHERE DATE(movement_date) = CURDATE()
"""
    
    def generate_sql(self, user_query: str) -> Optional[str]:
        """Generate SQL query using Gemini API"""
        try:
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"{self.system_prompt}\n\nUser Query: {user_query}"
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1000,
                    "topP": 0.8,
                    "topK": 10
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.gemini_url}?key={self.gemini_api_key}",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    generated_text = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Clean up the generated SQL
                    sql_query = self._clean_sql(generated_text)
                    return sql_query
                else:
                    logger.error(f"No candidates in Gemini response: {result}")
                    return None
            else:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            return None
    
    def _clean_sql(self, sql_text: str) -> str:
        """Clean and validate generated SQL"""
        # Remove markdown formatting
        sql_text = re.sub(r'```sql\s*', '', sql_text)
        sql_text = re.sub(r'```', '', sql_text)
        
        # Remove extra whitespace and normalize
        sql_text = ' '.join(sql_text.split())
        
        # Basic security check - only allow SELECT queries
        sql_upper = sql_text.upper().strip()
        if not sql_upper.startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed")
        
        # Check for dangerous keywords
        dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                raise ValueError(f"Dangerous keyword '{keyword}' not allowed")
        
        return sql_text
    
    def execute_sql(self, sql_query: str) -> Dict[str, Any]:
        """Execute SQL query and return results"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                
                # Get column names
                columns = [desc[0] for desc in cursor.description]
                
                # Fetch all results
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                data = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        # Handle different data types
                        if hasattr(value, 'isoformat'):  # datetime objects
                            row_dict[columns[i]] = value.isoformat()
                        elif isinstance(value, (int, float, str, bool)) or value is None:
                            row_dict[columns[i]] = value
                        else:
                            row_dict[columns[i]] = str(value)
                    data.append(row_dict)
                
                return {
                    'success': True,
                    'data': data,
                    'columns': columns,
                    'row_count': len(data),
                    'sql_query': sql_query
                }
                
        except Exception as e:
            logger.error(f"SQL execution error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'sql_query': sql_query
            }
    
    def suggest_chart_type(self, data: List[Dict], columns: List[str]) -> str:
        """Suggest appropriate chart type based on data structure"""
        if not data or len(data) == 0:
            return 'table'
        
        # Analyze data structure
        numeric_columns = []
        text_columns = []
        date_columns = []
        
        for col in columns:
            sample_values = [row.get(col) for row in data[:5] if row.get(col) is not None]
            
            if not sample_values:
                continue
                
            # Check for numeric data
            if all(isinstance(v, (int, float)) for v in sample_values):
                numeric_columns.append(col)
            # Check for date data
            elif any(isinstance(v, str) and ('date' in col.lower() or 'time' in col.lower()) for v in sample_values):
                date_columns.append(col)
            else:
                text_columns.append(col)
        
        # Chart type suggestions
        if len(numeric_columns) >= 1 and len(text_columns) >= 1:
            if len(data) <= 20:
                return 'bar'  # Bar chart for categorical data with values
            else:
                return 'line'  # Line chart for time series or large datasets
        elif len(numeric_columns) >= 2:
            return 'scatter'  # Scatter plot for numeric vs numeric
        elif len(text_columns) >= 1 and len(numeric_columns) >= 1:
            return 'pie'  # Pie chart for categories with single numeric value
        elif date_columns and numeric_columns:
            return 'line'  # Time series
        else:
            return 'table'  # Default to table view
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Main method to process user query and return results with chart suggestion"""
        try:
            # Step 1: Generate SQL
            sql_query = self.generate_sql(user_query)
            if not sql_query:
                return {
                    'success': False,
                    'error': 'Failed to generate SQL query from your request'
                }
            
            # Step 2: Execute SQL
            result = self.execute_sql(sql_query)
            if not result['success']:
                return result
            
            # Step 3: Suggest chart type
            chart_type = self.suggest_chart_type(result['data'], result['columns'])
            
            # Step 4: Add chart suggestion to result
            result['chart_type'] = chart_type
            result['user_query'] = user_query
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                'success': False,
                'error': f'Processing error: {str(e)}'
            }


###################################################################################
# VIEW FUNCTIONS
###################################################################################
@csrf_exempt
@require_http_methods(["GET", "POST"])
def smart_assistant(request):
    """Main smart assistant view"""
    if request.method == 'GET':
        # Return the assistant interface
        return render(request, 'web/smart_assistant.html')
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_query = data.get('query', '').strip()
            
            if not user_query:
                return JsonResponse({
                    'success': False,
                    'error': 'Please provide a query'
                }, status=400)
            
            # Initialize assistant
            assistant = SmartAssistant()
            
            # Process the query
            result = assistant.process_query(user_query)
            
            return JsonResponse(result)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request'
            }, status=400)
        except Exception as e:
            logger.error(f"Smart assistant error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Server error: {str(e)}'
            }, status=500)


@require_http_methods(["GET"])
def get_query_suggestions(request):
    """Get sample query suggestions for users"""
    suggestions = [
        {
            'category': 'Inventory Analysis',
            'queries': [
                'Show me top 10 products by total stock',
                'Which products are low on stock?',
                'Show inventory levels by warehouse',
                'Products with zero stock across all warehouses',
                'Most stocked products in BLR7 warehouse'
            ]
        },
        {
            'category': 'Sales Analytics',
            'queries': [
                'Total sales by marketplace this month',
                'Top selling products by quantity',
                'Average order value by marketplace',
                'Orders shipped in the last 7 days',
                'Revenue comparison between marketplaces'
            ]
        },
        {
            'category': 'Product Performance',
            'queries': [
                'Best performing products by revenue',
                'Products with highest profit margins',
                'Combo products and their components',
                'Active vs inactive product counts',
                'Products by category and brand'
            ]
        },
        {
            'category': 'Warehouse Operations',
            'queries': [
                'Inventory movements today',
                'Stock transfers between warehouses',
                'Warehouse utilization rates',
                'Inbound vs outbound movements',
                'Products needing restock'
            ]
        }
    ]
    
    return JsonResponse({
        'success': True,
        'suggestions': suggestions
    })