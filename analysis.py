#!/usr/bin/env python
# coding: utf-8

# # Olist Analysis

# In[1]:


get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')


# In[2]:


import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from olist.data import Olist
from olist.order import Order
from olist.seller import Seller
from olist.product import Product
from olist.review import Review

from bi_data import (
    sales,
    sales_by_period,
    sales_by_customer_state,
    sales_by_seller_state,
)


# ## Your analysis
# 
# Start your analysis here. Remember to keep your notebook nice and tidy!
# 
# - Use **Markdown** headings (using hashtags #, ##, ###) to structure your notebook.
# - Those headings allow you to collapse parts of your notebook.
# - Merge / split code cells to make them easy to run together / separately.
# - Make sure your notebook is runnable from top to bottom. Regularly restart your kernel and run the notebook to check.

# # Olist Analysis – Growth & Customer Satisfaction
# 
# **Group members:** [Add your names here]  
# **Audience:** CEO & Investors  
# **Objective:** Understand Olist’s sales performance and customer satisfaction in 2017–2018
# 
# ---
# 
# ## 1. Business Context
# 
# Olist has shown strong growth, but customer experience varies significantly.  
# In this analysis we explore:
# - How sales have evolved over time
# - Where sales are concentrated geographically
# - Which product categories drive revenue vs customer satisfaction
# 
# ---
# 
# ## 2. Data Preparation
# 
# We use the `bi_data` module which provides clean, ready-to-use tables.

# In[3]:


print("Data loaded successfully")
print(f"Total orders in sales table: {len(sales()):,}")


# ## 3. Visual 1: Sales Evolution Over Time
# 
# **Question:** Is Olist growing?

# In[4]:


# Monthly sales (aggregated by customer state)
monthly_sales = sales_by_period('ME')

fig1 = px.line(
    monthly_sales,
    x='order_purchase_timestamp',
    y='sales',
    color='customer_state',
    title='Monthly Sales Evolution by Customer State',
    labels={'order_purchase_timestamp': 'Month', 'sales': 'Sales (BRL)'},
    template='plotly_white'
)

fig1.update_layout(
    legend_title_text='Customer State',
    height=500
)

fig1.show()


# **Insight:**  
# Olist shows clear growth in 2017 and early 2018, with sales heavily concentrated in a few states (especially SP).

# ## 4. Visual 2: Sales Concentration by State
# 
# **Question:** Where does Olist make most of its revenue?

# In[5]:


state_sales = sales_by_customer_state().sort_values('sales', ascending=False)

fig2 = px.bar(
    state_sales.head(10),
    x='customer_state',
    y='sales',
    color='sales',
    title='Top 10 States by Total Sales',
    labels={'customer_state': 'State', 'sales': 'Total Sales (BRL)'},
    color_continuous_scale='Blues',
    template='plotly_white'
)

fig2.update_layout(height=500)
fig2.show()


# **Insight:**  
# More than 50% of Olist’s revenue comes from São Paulo (SP).  
# This concentration represents both an opportunity and a risk.

# ## 5. Visual 3: Customer Satisfaction by Product Category *(Optional but recommended)*
# 
# We will add this one together if you have time.

# ## 6. Key Takeaways & Recommendations
# 
# - Olist is growing, but growth is heavily concentrated in a few states and categories.
# - Customer satisfaction varies significantly across product categories.
# - Improving delivery performance in lower-performing categories could have a big impact on overall satisfaction.
# 
# 

# --------------

# # Where does Olist actually makes its money?

# ## Sales Concentration by State
# 
# **Business Question:** Which states generate the most revenue for Olist?

# In[6]:


# Load the aggregated data by customer state
state_sales = sales_by_customer_state()

# Sort by sales (highest first)
state_sales = state_sales.sort_values('sales', ascending=False)

# Create the bar chart
fig_state = px.bar(
    state_sales.head(10),                    # Show only top 10 states
    x='customer_state',
    y='sales',
    color='sales',                           # Color by sales value
    color_continuous_scale='Blues',          # Nice blue gradient
    title='Top 10 States by Total Sales Revenue',
    labels={
        'customer_state': 'Customer State',
        'sales': 'Total Sales (BRL)'
    },
    template='plotly_white'                  # Clean background
)

# Improve layout
fig_state.update_layout(
    height=550,
    xaxis_tickangle=-45,                     # Rotate state labels
    coloraxis_colorbar_title='Sales (BRL)'
)

fig_state.show()


# **Key Insight:**
# 
# - São Paulo (**SP**) generates by far the largest share of Olist’s revenue.
# - The top 3 states (SP, RJ, MG) represent a very large portion of total sales.
# - This shows strong geographic concentration → both an opportunity and a risk for Olist.

# In[7]:


# Load and sort data (highest sales on top)
state_sales = sales_by_customer_state().sort_values('sales', ascending=True)

# Create horizontal bar chart with ALL states
fig_state = px.bar(
    state_sales,
    x='sales',
    y='customer_state',
    orientation='h',                           # ← Horizontal bars
    color='sales',
    color_continuous_scale='Blues',
    title='Sales Revenue by Customer State (All States)',
    labels={
        'customer_state': 'Customer State',
        'sales': 'Total Sales (BRL)'
    },
    template='plotly_white'
)

# Improve readability
fig_state.update_layout(
    height=900,                                # Make chart taller
    yaxis={'categoryorder': 'total ascending'},# Sort from lowest to highest
    coloraxis_colorbar_title='Sales (BRL)'
)

# Add value labels on the bars
fig_state.update_traces(
    texttemplate='%{x:,.0f}',
    textposition='outside'
)

fig_state.show()


# **Observation:**
# 
# While São Paulo dominates, there are many states with very low sales.  
# This could represent growth opportunities for Olist in the future.

# --------------------------------

# # relative distribution of sales

# In[8]:


# Get sales by state
state_sales = sales_by_customer_state()

# Calculate percentage of total sales
total_sales = state_sales['sales'].sum()
state_sales['sales_pct'] = (state_sales['sales'] / total_sales * 100).round(2)

# Sort from highest to lowest
state_sales = state_sales.sort_values('sales', ascending=False)

# Calculate cumulative percentage (very useful insight!)
state_sales['cumulative_pct'] = state_sales['sales_pct'].cumsum().round(2)

# Show the top 10 to understand the pattern
state_sales[['customer_state', 'sales', 'sales_pct', 'cumulative_pct']].head(10)


# In[10]:


fig_pct = px.bar(
    state_sales,
    x='sales_pct',
    y='customer_state',
    orientation='h',
    color='sales_pct',
    color_continuous_scale='Blues',
    title='Percentage of Total Sales by Customer State',
    labels={
        'customer_state': 'Customer State',
        'sales_pct': 'Share of Total Sales (%)'
    },
    template='plotly_white'
)

fig_pct.update_layout(
    height=900,
    yaxis={'categoryorder': 'total ascending'}
)

fig_pct.update_traces(
    texttemplate='%{x:.1f}%',
    textposition='outside'
)

fig_pct.show()


# 

# In[11]:


fig_cum = px.line(
    state_sales.reset_index(),
    x='customer_state',
    y='cumulative_pct',
    markers=True,
    title='Cumulative Sales Percentage (Pareto View)',
    labels={
        'customer_state': 'State (sorted by sales)',
        'cumulative_pct': 'Cumulative % of Total Sales'
    },
    template='plotly_white'
)

fig_cum.add_hline(y=80, line_dash="dash", line_color="red",
                  annotation_text="80% line")

fig_cum.update_layout(height=500)
fig_cum.show()


# 

# ## Sales Concentration Analysis
# 
# **Key Finding:**
# 
# - The top **3 states** (SP, RJ, MG) represent approximately **64%** of total revenue.
# - More than half of Brazilian states contribute less than 1% each.
# - This shows **high geographic concentration** of Olist’s business.
# 
# **Implication for Olist:**
# Olist is heavily dependent on a few key states. Expanding successfully into lower-performing states could be a major growth opportunity.

# --------------------------------------

# ## Brazil Sales Map – Highlighting Low Contribution States
# 
# This choropleth map shows total sales by state across Brazil.
# States that contribute **less than 2%** of Olist’s total sales are colored **white**, while states with higher contributions are shown in shades of blue (darker = higher sales).
# 
# This visualization makes it easy to see the strong geographic concentration of Olist’s revenue.

# In[15]:


import requests
import json

# Load Brazilian states GeoJSON (public file)
geojson_url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
brazil_geo = requests.get(geojson_url).json()

# Create the choropleth map
fig_map = px.choropleth(
    state_sales,
    geojson=brazil_geo,
    locations='customer_state',           # Must match the state codes in your dataframe (SP, RJ, MG...)
    featureidkey="properties.sigla",      # This tells Plotly how to match states in the GeoJSON
    color='sales',
    color_continuous_scale='Blues',
    title='Olist Sales by State in Brazil',
    labels={'sales': 'Total Sales (BRL)'},
    hover_name='customer_state',
    hover_data={'sales': ':,.0f'}
)

# Center and zoom on Brazil
fig_map.update_geos(
    center=dict(lat=-14.2, lon=-51.9),   # Center of Brazil
    projection_scale=4.5,                # Zoom level
    showcountries=True,
    showcoastlines=True
)

fig_map.update_layout(
    height=700,
    margin={"r":0,"t":60,"l":0,"b":0},
    title={
        'text': 'Olist Sales Distribution Across Brazilian States<br><sup>Darker = Higher Sales</sup>',
        'x': 0.5
    }
)

fig_map.show()


# -----------------------

# # negative reviews per state with less than 2% of total sales

# ## Sales vs Negative Reviews by State
# 
# We combined sales data with review data to analyze the relationship between revenue contribution and customer satisfaction per state.  
# 
# Negative reviews were defined as orders with a **review score ≤ 3**.  
# For each state, we calculated:
# - Share of total sales (%)
# - Percentage of negative reviews
# - Total number of reviews received
# 
# This allows us to identify states that generate little revenue but have disproportionately high rates of customer dissatisfaction.

# In[16]:


from olist.data import Olist

# Get raw data
data = Olist().get_data()
reviews = data['order_reviews'][['order_id', 'review_score']].copy()
orders = sales()[['order_id', 'customer_state']].copy()

# Merge reviews with orders (to get customer_state)
reviews_with_state = reviews.merge(orders, on='order_id', how='inner')

# Calculate negative reviews (score ≤ 3)
reviews_with_state['is_negative'] = reviews_with_state['review_score'] <= 3

# Aggregate by state
review_by_state = (
    reviews_with_state
    .groupby('customer_state')
    .agg(
        total_reviews=('review_score', 'count'),
        negative_reviews=('is_negative', 'sum')
    )
    .reset_index()
)

review_by_state['negative_review_pct'] = (
    review_by_state['negative_reviews'] / review_by_state['total_reviews'] * 100
).round(2)

# Merge with sales data
state_analysis = state_sales[['customer_state', 'sales', 'sales_pct']].merge(
    review_by_state[['customer_state', 'negative_review_pct', 'total_reviews']],
    on='customer_state',
    how='left'
)

# Show states with low sales but high negative reviews
low_sales_high_negative = state_analysis[
    (state_analysis['sales_pct'] < 2) &
    (state_analysis['negative_review_pct'] > state_analysis['negative_review_pct'].mean())
].sort_values('negative_review_pct', ascending=False)

low_sales_high_negative


# In[17]:


print("Average negative review rate across all states:",
      round(state_analysis['negative_review_pct'].mean(), 2), "%")


# In[ ]:


fig = px.scatter(
    state_analysis,
    x='sales_pct',
    y='negative_review_pct',
    size='total_reviews',
    color='sales_pct',
    hover_name='customer_state',
    title='Sales Share vs Negative Review Rate by State',
    labels={
        'sales_pct': 'Share of Total Sales (%)',
        'negative_review_pct': 'Negative Reviews (%)'
    },
    template='plotly_white'
)

# Add average lines
fig.add_hline(y=state_analysis['negative_review_pct'].mean(),
              line_dash="dash", line_color="red",
              annotation_text="Average negative review rate")

fig.add_vline(x=2, line_dash="dash", line_color="gray",
              annotation_text="2% sales threshold")

fig.update_layout(height=600)
fig.show()


# ## States with Above-Average Negative Review Rates
# 
# This map highlights Brazilian states that have a **negative review rate above the national average**.  
# 
# - **Red states** = Above-average percentage of negative reviews (review score ≤ 3)  
# - **Gray states** = Average or below-average negative review rates  
# 
# This visualization helps identify states where poor customer experience may be damaging Olist’s reputation, even if they currently contribute little revenue.

# In[19]:


import requests

# Load Brazilian states GeoJSON
geojson_url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
brazil_geo = requests.get(geojson_url).json()

# Calculate average negative review rate
avg_negative = state_analysis['negative_review_pct'].mean()

# Create a categorical column for coloring
state_analysis['review_performance'] = state_analysis['negative_review_pct'].apply(
    lambda x: 'Above Average' if x > avg_negative else 'Below or Equal Average'
)

# Create the map
fig = px.choropleth(
    state_analysis,
    geojson=brazil_geo,
    locations='customer_state',
    featureidkey="properties.sigla",
    color='review_performance',
    color_discrete_map={
        'Above Average': '#d62728',           # Red
        'Below or Equal Average': '#d3d3d3'   # Light gray
    },
    title=f'Brazilian States with Above-Average Negative Reviews<br><sup>Red = Above average ({avg_negative:.1f}% negative reviews)</sup>',
    hover_name='customer_state',
    hover_data={
        'negative_review_pct': ':.2f',
        'sales_pct': ':.2f',
        'total_reviews': True
    }
)

fig.update_geos(
    center=dict(lat=-14.2, lon=-51.9),
    projection_scale=4.5,
    showcountries=True,
    showcoastlines=True
)

fig.update_layout(
    height=700,
    margin={"r":0,"t":70,"l":0,"b":0}
)

fig.show()


# ## Combined Map: Sales Contribution vs Negative Reviews
# 
# This choropleth map combines sales performance and customer satisfaction at the state level.
# 
# States are classified into three categories:
# 
# - **Red**: States that contribute **less than 2%** of total sales **and** have an **above-average** negative review rate (review score ≤ 3). These states generate little revenue while creating a disproportionately high number of dissatisfied customers.
# - **Gray**: Low-sales states (< 2%) with average or below-average negative review rates.
# - **Blue**: High-sales states (≥ 2% of total revenue), regardless of review performance.
# 
# This visualization highlights potentially problematic states where low revenue contribution is combined with poor customer experience.

# In[23]:


import requests

# Load Brazilian states GeoJSON
geojson_url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
brazil_geo = requests.get(geojson_url).json()

# Calculate average negative review rate
avg_negative = state_analysis['negative_review_pct'].mean()

# Create clear categories
def categorize_state(row):
    if row['sales_pct'] < 2 and row['negative_review_pct'] > avg_negative:
        return 'Low Sales + High Negative Reviews'
    elif row['sales_pct'] < 2:
        return 'Low Sales + Average/Below Negative Reviews'
    else:
        return 'High Sales States (≥ 2%)'

state_analysis['state_category'] = state_analysis.apply(categorize_state, axis=1)

# Create the fused map
fig = px.choropleth(
    state_analysis,
    geojson=brazil_geo,
    locations='customer_state',
    featureidkey="properties.sigla",
    color='state_category',
    color_discrete_map={
        'Low Sales + High Negative Reviews': '#d62728',           # Red (key group)
        'Low Sales + Average/Below Negative Reviews': '#d3d3d3',  # Light gray
        'High Sales States (≥ 2%)': '#1f77b4'                     # Blue
    },
    title='Brazil Sales vs Customer Satisfaction by State<br><sup>Red = Low Sales (<2%) + Above-Average Negative Reviews</sup>',
    hover_name='customer_state',
    hover_data={
        'sales_pct': ':.2f',
        'negative_review_pct': ':.2f',
        'total_reviews': True
    }
)

fig.update_geos(
    center=dict(lat=-14.2, lon=-51.9),
    projection_scale=4.5,
    showcountries=True,
    showcoastlines=True
)

fig.update_layout(
    height=700,
    margin={"r":0,"t":70,"l":0,"b":0},
    legend_title_text='State Category'
)

fig.show()


# ## Insight: Several Brazilian states generate very low revenue for Olist while producing above-average negative reviews. These states represent a reputational risk with limited financial upside.
# ## Action: Investigate the root causes of poor customer experience in these states to protect brand reputation.
