import argparse
import requests
from bs4 import BeautifulSoup
import pandas as pd
import getpass
import time
from typing import List, Dict, Optional
import json

# === Configuration ===
APOLLO_API_BASE_URL = "https://api.apollo.io/api/v1"
GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={}"

# === Apollo API Functions ===
def fetch_leads_from_apollo(api_key: str, company_size: str, industry: str, location: str = "", limit: int = 10) -> List[Dict]:
    """Fetch real leads using Apollo API"""
    url = f"{APOLLO_API_BASE_URL}/mixed_people/search"
    
    # Parse company size range
    try:
        if "-" in company_size:
            min_size, max_size = map(int, company_size.split("-"))
        else:
            min_size = max_size = int(company_size)
    except ValueError:
        print(f"Warning: Invalid company size format '{company_size}'. Using default range 50-200.")
        min_size, max_size = 50, 200

    headers = {
        "Cache-Control": "no-cache", 
        "Content-Type": "application/json",
        "X-Api-Key": api_key
    }
    
    # Build search criteria
    payload = {
        "q_organization_num_employees_ranges": [f"{min_size},{max_size}"],
        "page": 1,
        "per_page": limit,
        "organization_locations": [location] if location else [],
        "q_organization_keyword_tags": [industry] if industry else []
    }
    
    try:
        print(f"Searching Apollo for companies: {company_size} employees, {industry} industry...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        leads = []
        
        if 'organizations' in data:
            for org in data['organizations']:
                leads.append({
                    "company_name": org.get('name', 'Unknown'),
                    "website": org.get('website_url', ''),
                    "employee_count": org.get('estimated_num_employees', 0),
                    "industry": org.get('industry', ''),
                    "apollo_id": org.get('id', ''),
                    "description": org.get('short_description', ''),
                    "location": org.get('primary_location', {}).get('city', '') if org.get('primary_location') else ''
                })
        elif 'companies' in data:
            # Handle alternative response format
            for org in data['companies']:
                leads.append({
                    "company_name": org.get('name', 'Unknown'),
                    "website": org.get('website_url', ''),
                    "employee_count": org.get('estimated_num_employees', 0),
                    "industry": org.get('industry', ''),
                    "apollo_id": org.get('id', ''),
                    "description": org.get('short_description', ''),
                    "location": org.get('primary_location', {}).get('city', '') if org.get('primary_location') else ''
                })
        
        print(f"✅ Found {len(leads)} companies from Apollo")
        return leads
        
    except requests.RequestException as e:
        print(f"❌ Apollo API Error: {e}")
        print("Falling back to simulated data...")
        return get_simulated_leads()
    except Exception as e:
        print(f"❌ Error processing Apollo response: {e}")
        print("Falling back to simulated data...")
        return get_simulated_leads()

def get_simulated_leads() -> List[Dict]:
    """Fallback simulated data if Apollo fails"""
    return [
        {
            "company_name": "Basecamp", 
            "website": "https://basecamp.com", 
            "employee_count": 60,
            "industry": "Software",
            "apollo_id": "sim_1",
            "description": "Project management and team collaboration software",
            "location": "Chicago"
        },
        {
            "company_name": "Trello", 
            "website": "https://trello.com", 
            "employee_count": 100,
            "industry": "Software", 
            "apollo_id": "sim_2",
            "description": "Visual project management tool using boards and cards",
            "location": "New York"
        }
    ]

def enrich_with_apollo_details(api_key: str, apollo_id: str) -> Dict:
    """Get additional company details from Apollo"""
    if apollo_id.startswith('sim_'):
        return {}  # Skip simulated data
        
    url = f"{APOLLO_API_BASE_URL}/organizations/{apollo_id}"
    
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json", 
        "X-Api-Key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        org = data.get('organization', {})
        
        return {
            "technologies": [tech.get('name', '') for tech in org.get('technologies', [])[:5]],
            "funding_stage": org.get('funding_stage', ''),
            "total_funding": org.get('total_funding', 0),
            "recent_news": [news.get('title', '') for news in org.get('recent_news', [])[:2]]
        }
        
    except Exception as e:
        print(f"Warning: Could not fetch additional details for {apollo_id}: {e}")
        return {}

# === Web Scraping for Additional Insights ===
def scrape_insights(website_url: str) -> List[str]:
    """Scrape company insights from website"""
    if not website_url or website_url == '':
        return ["No website available"]
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(website_url, timeout=10, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Try to get meta description first
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        insights = []
        
        if meta_desc and meta_desc.get('content'):
            insights.append(meta_desc.get('content'))
        
        # Get paragraphs
        paragraphs = soup.find_all("p")
        para_texts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40]
        insights.extend(para_texts[:2])
        
        return insights[:3] if insights else ["No insights available"]
        
    except requests.RequestException as e:
        print(f"Warning: Could not retrieve data from {website_url}: {e}")
        return [f"Could not access website: {website_url}"]
    except Exception as e:
        print(f"Error processing {website_url}: {e}")
        return [f"Error processing {website_url}"]

# === Gemini API Functions ===
def get_gemini_api_key() -> str:
    """Get Gemini API key (your provided key)"""
    return "AIzaSyDt30zNxdamtyjrn4MxEHg2zLRqwsXATW8"  # Your provided Gemini API key

def gemini_generate_text(api_key: str, prompt_text: str, temperature: float = 0, 
                        top_p: float = 0.9, top_k: int = 40) -> Optional[str]:
    """Generate text using Gemini API"""
    url = GEMINI_API_URL_TEMPLATE.format(api_key)
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt_text
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "topP": top_p,
            "topK": top_k
        }
    }
    
    try:
        response = requests.post(url, headers={"Content-Type": "application/json"}, 
                               json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Handle different response formats
        if 'candidates' in result and result['candidates']:
            return result['candidates'][0]['content']['parts'][0]['text']
        elif 'contents' in result:
            return result['contents'][0]['parts'][0]['text']
        else:
            print("Unexpected response format from Gemini API")
            return None
            
    except requests.RequestException as e:
        print(f"Gemini API Error: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Error parsing Gemini response: {e}")
        return None

def create_outreach_prompt(company_data: Dict, insights: List[str], apollo_details: Dict) -> str:
    """Create personalized outreach prompt with Apollo and web scraped data"""
    
    # Combine all available information
    company_name = company_data.get('company_name', '')
    website = company_data.get('website', '')
    employee_count = company_data.get('employee_count', 0)
    industry = company_data.get('industry', '')
    description = company_data.get('description', '')
    location = company_data.get('location', '')
    
    # Apollo enriched data
    technologies = ', '.join(apollo_details.get('technologies', []))
    funding_stage = apollo_details.get('funding_stage', '')
    recent_news = ', '.join(apollo_details.get('recent_news', []))
    
    # Web scraped insights
    web_insights = ' '.join(insights)
    
    return f"""
You are an AI sales assistant helping to generate personalized B2B outreach messages for potential leads based on enriched company data from Apollo and web research.

My company details: 
My Name: Vishwash Sharma
Company Name: Vishwash Tech Solutions
My Website: https://www.vishwashtechsolutions.com

Target Company Information:
Company Name: {company_name}
Website: {website}
Employee Count: {employee_count}
Industry: {industry}
Location: {location}
Description: {description}
Technologies Used: {technologies}
Funding Stage: {funding_stage}
Recent News: {recent_news}
Website Insights: {web_insights}

Objective:
Generate a professional, concise, and personalized B2B outreach message that includes:
- A reference to specific details about their company (industry, technology stack, recent news, or growth)
- A value proposition highlighting how our hardware solutions can benefit their specific business needs
- A professional tone appropriate for cold outreach via email or LinkedIn

Format:
- Personalized greeting with company name
- Specific insight or compliment based on their business/technology/growth
- Tailored pitch of relevant hardware solution(s) for their industry/size
- Clear call to action (scheduling a brief call)

Requirements:
- Keep message under 120 words
- Avoid generic templated phrasing
- Focus on relevance and personalization based on the data provided
- Use actual names directly (no placeholders)
- Make it feel human and genuine
- ONLY RETURN THE GENERATED MESSAGE, NOTHING ELSE NO EXTRA COMMENTS OR EXPLANATIONS
"""

def generate_outreach_messages(apollo_key: str, gemini_key: str, input_file: str = 'lead_outreach.xlsx', 
                             output_file: str = 'enriched_outreach_messages.xlsx') -> None:
    """Generate outreach messages for all leads using Gemini"""
    try:
        # Load input data
        data = pd.read_excel(input_file)
        print(f"Loaded {len(data)} leads from {input_file}")
        
        # Prepare output data
        output_data = []
        
        # Process each lead
        for index, row in data.iterrows():
            company_name = row['Company Name']
            apollo_id = row.get('Apollo ID', '')
            
            print(f"Generating message for {company_name}...")
            
            # Get Apollo enrichment if available
            apollo_details = enrich_with_apollo_details(apollo_key, apollo_id) if apollo_id else {}
            
            # Prepare company data
            company_data = {
                'company_name': company_name,
                'website': row.get('Website', ''),
                'employee_count': row.get('Employee Count', 0),
                'industry': row.get('Industry', ''),
                'description': row.get('Description', ''),
                'location': row.get('Location', '')
            }
            
            # Combine insights
            insights = [
                str(row.get('Insight 1', '')),
                str(row.get('Insight 2', '')),
                str(row.get('Insight 3', ''))
            ]
            insights = [i for i in insights if i and i != 'nan']
            
            # Create prompt and generate message
            prompt = create_outreach_prompt(company_data, insights, apollo_details)
            message = gemini_generate_text(gemini_key, prompt)
            
            if message:
                print(f"✅ Message generated for {company_name}")
            else:
                message = "Failed to generate message."
                print(f"❌ Failed to generate message for {company_name}")
            
            # Add to output data
            output_data.append({
                'Company Name': company_name,
                'Website': company_data['website'],
                'Employee Count': company_data['employee_count'],
                'Industry': company_data['industry'],
                'Generated Message': message
            })
            
            # Small delay to avoid rate limiting
            time.sleep(1)
        
        # Save all results at once
        output_df = pd.DataFrame(output_data)
        output_df.to_excel(output_file, index=False)
        print(f"✅ All outreach messages saved to '{output_file}'")
        
    except FileNotFoundError:
        print(f"Error: Could not find input file '{input_file}'")
    except Exception as e:
        print(f"Error generating outreach messages: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Lead Generator with Apollo + Gemini Outreach")
    parser.add_argument("--size", type=str, required=True, help="Company size range (e.g., '50-200')")
    parser.add_argument("--industry", type=str, required=True, help="Industry (e.g., 'software')")
    parser.add_argument("--location", type=str, default="", help="Location (optional)")
    parser.add_argument("--limit", type=int, default=10, help="Number of leads to fetch (default: 10)")
    parser.add_argument("--skip-generation", action="store_true", 
                       help="Skip outreach message generation")
    
    args = parser.parse_args()
    
    # Apollo API key (you provided this)
    APOLLO_API_KEY = "Cumjivr16UxkBq8lwNTtug"
    
    try:
        # Step 1: Fetch leads from Apollo
        print("Fetching leads from Apollo...")
        leads = fetch_leads_from_apollo(APOLLO_API_KEY, args.size, args.industry, args.location, args.limit)
        
        if not leads:
            print("No leads found. Exiting.")
            return
        
        all_data = []
        
        # Step 2: Scrape insights and enrich data
        print("Enriching lead data...")
        for lead in leads:
            print(f"Processing {lead['company_name']}...")
            
            # Scrape website insights
            insights = scrape_insights(lead["website"])
            
            lead_data = {
                "Company Name": lead["company_name"],
                "Website": lead["website"],
                "Employee Count": lead["employee_count"],
                "Industry": lead["industry"],
                "Description": lead["description"],
                "Location": lead["location"],
                "Apollo ID": lead["apollo_id"],
                "Insight 1": insights[0] if len(insights) > 0 else "",
                "Insight 2": insights[1] if len(insights) > 1 else "",
                "Insight 3": insights[2] if len(insights) > 2 else ""
            }
            all_data.append(lead_data)
            
            # Small delay between requests
            time.sleep(0.5)
        
        # Step 3: Save leads data
        df = pd.DataFrame(all_data)
        df.to_excel("lead_outreach.xlsx", index=False)
        print("✅ Leads saved to 'lead_outreach.xlsx'")
        
        # Step 4: Generate outreach messages (if not skipped)
        if not args.skip_generation:
            print("\nGenerating outreach messages with Gemini...")
            gemini_key = get_gemini_api_key()
            generate_outreach_messages(APOLLO_API_KEY, gemini_key)
        else:
            print("Skipping outreach message generation (remove --skip-generation to enable)")
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()