#!/usr/bin/env python3
"""
Ollama Business Contact Enhancer

This script uses local AI (Ollama) running on your GPU to enhance business search
for businesses where traditional Google Places lookup failed. It can:

1. Generate alternative business names/search terms
2. Suggest social media handles
3. Identify potential business websites
4. Create targeted search strategies

This is designed for the "No_Contacts_Found" CSV from the main lookup script.
Requires Ollama to be installed and running locally.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OllamaBusinessEnhancer:
    """
    Uses local Ollama AI to enhance business search strategies
    """
    
    def __init__(self, ollama_host="http://localhost:11434", model="llama3.1"):
        self.ollama_host = ollama_host
        self.model = model
        self.enhanced_businesses = []
        
    def check_ollama_connection(self):
        """
        Check if Ollama is running and accessible
        """
        try:
            response = requests.get(f"{self.ollama_host}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                available_models = [m['name'] for m in models]
                logger.info(f"✅ Ollama connected. Available models: {available_models}")
                
                if self.model not in available_models:
                    logger.warning(f"Model {self.model} not found. Using first available: {available_models[0] if available_models else 'none'}")
                    if available_models:
                        self.model = available_models[0]
                
                return True
            else:
                logger.error(f"Ollama responded with status {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error("❌ Cannot connect to Ollama. Make sure it's running with: 'ollama serve'")
            return False
        except Exception as e:
            logger.error(f"Error checking Ollama connection: {e}")
            return False
    
    def generate_ai_prompt(self, business_data):
        """
        Create an AI prompt for enhancing business search
        """
        name = business_data.get('Name', '')
        address = business_data.get('Address', '')
        suburb = business_data.get('Suburb', '')
        licensee = business_data.get('Licensee', '')
        
        prompt = f"""
You are a business research expert helping find contact details for Australian restaurants, bars, and hospitality businesses.

Business Details:
- Name: {name}
- Address: {address}
- Suburb: {suburb}, NSW
- Licensee/Owner: {licensee}

The business has an active liquor license but initial Google Places search didn't find contact details.

Please suggest:
1. Alternative business names to search for (they might operate under a different name)
2. Potential social media handles (Instagram, Facebook)
3. Likely website domain patterns
4. Search strategies specific to this business type and location

Respond in JSON format:
{{
    "alternative_names": ["name1", "name2"],
    "social_handles": {{
        "instagram": ["@handle1", "@handle2"],
        "facebook": ["PageName1", "PageName2"]
    }},
    "website_patterns": ["domain1.com.au", "domain2.com"],
    "search_strategies": ["strategy1", "strategy2"],
    "confidence_score": 0.8
}}

Focus on realistic, Australian business naming patterns and local hospitality industry conventions.
"""
        return prompt
    
    def query_ollama(self, prompt):
        """
        Send a query to Ollama and get response
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower temperature for more focused responses
                    "top_p": 0.8
                }
            }
            
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error querying Ollama: {e}")
            return None
    
    def parse_ai_response(self, response_text):
        """
        Parse AI response and extract structured data
        """
        try:
            # Try to extract JSON from the response
            # Sometimes AI responses include extra text before/after JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                logger.warning("No valid JSON found in AI response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing AI JSON response: {e}")
            return None
    
    def enhance_business(self, business_data):
        """
        Use AI to enhance a single business record
        """
        name = business_data.get('Name', '')
        logger.info(f"🤖 Enhancing search strategy for: {name}")
        
        # Generate AI prompt
        prompt = self.generate_ai_prompt(business_data)
        
        # Query Ollama
        ai_response = self.query_ollama(prompt)
        if not ai_response:
            return None
        
        # Parse response
        enhanced_data = self.parse_ai_response(ai_response)
        if not enhanced_data:
            return None
        
        # Combine original data with AI enhancements
        enhanced_business = business_data.copy()
        enhanced_business.update({
            'AI_Alternative_Names': ', '.join(enhanced_data.get('alternative_names', [])),
            'AI_Instagram_Handles': ', '.join(enhanced_data.get('social_handles', {}).get('instagram', [])),
            'AI_Facebook_Pages': ', '.join(enhanced_data.get('social_handles', {}).get('facebook', [])),
            'AI_Website_Patterns': ', '.join(enhanced_data.get('website_patterns', [])),
            'AI_Search_Strategies': ' | '.join(enhanced_data.get('search_strategies', [])),
            'AI_Confidence_Score': enhanced_data.get('confidence_score', 0.0),
            'AI_Enhanced_Date': datetime.now().strftime('%Y-%m-%d %H:%M')
        })
        
        logger.info(f"✨ Generated {len(enhanced_data.get('alternative_names', []))} alternative names, {len(enhanced_data.get('website_patterns', []))} website patterns")
        
        return enhanced_business
    
    def process_no_contacts_csv(self, csv_file, max_businesses=10):
        """
        Process the "No_Contacts_Found" CSV and enhance with AI suggestions
        """
        logger.info("🚀 Starting AI-enhanced business processing...")
        
        # Check Ollama connection
        if not self.check_ollama_connection():
            logger.error("Cannot proceed without Ollama connection")
            return None
        
        # Load CSV
        try:
            df = pd.read_csv(csv_file)
            logger.info(f"Loaded {len(df)} businesses needing enhancement")
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            return None
        
        # Process limited number of businesses
        processing_df = df.head(max_businesses)
        logger.info(f"Processing first {len(processing_df)} businesses (GPU/time limit)")
        
        enhanced_businesses = []
        
        for idx, (_, row) in enumerate(processing_df.iterrows(), 1):
            logger.info(f"\n--- Processing {idx}/{len(processing_df)} ---")
            
            enhanced_business = self.enhance_business(row)
            if enhanced_business:
                enhanced_businesses.append(enhanced_business)
            
            # Brief pause to avoid overwhelming the GPU
            import time
            time.sleep(1)
        
        # Save enhanced results
        if enhanced_businesses:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            output_file = f"data/AI_Enhanced_Businesses_{timestamp}.csv"
            
            enhanced_df = pd.DataFrame(enhanced_businesses)
            enhanced_df.to_csv(output_file, index=False)
            
            logger.info(f"✅ AI-enhanced businesses saved to: {output_file}")
            logger.info(f"📊 Enhanced {len(enhanced_businesses)} businesses with AI suggestions")
        
        return enhanced_businesses


def main():
    """
    Main function for AI enhancement
    """
    # Configuration
    NO_CONTACTS_FILE = "data/No_Contacts_Found_20250809_2247.csv"  # Update with your actual file
    OLLAMA_HOST = "http://localhost:11434"
    MODEL = "llama3.1"  # Change to your preferred model
    MAX_BUSINESSES = 5  # Start small for testing
    
    # Validate input file
    if not Path(NO_CONTACTS_FILE).exists():
        logger.error(f"No contacts file not found: {NO_CONTACTS_FILE}")
        logger.info("Please run the main contact lookup script first to generate this file")
        return
    
    # Initialize enhancer
    enhancer = OllamaBusinessEnhancer(ollama_host=OLLAMA_HOST, model=MODEL)
    
    # Process businesses
    try:
        enhanced_businesses = enhancer.process_no_contacts_csv(
            NO_CONTACTS_FILE,
            max_businesses=MAX_BUSINESSES
        )
        
        if enhanced_businesses:
            logger.info("\n🎉 AI enhancement completed!")
            logger.info("Next steps:")
            logger.info("1. Review the AI_Enhanced_Businesses_*.csv file")
            logger.info("2. Use the alternative names and website patterns for manual searches")
            logger.info("3. Check suggested social media handles")
            logger.info("4. Consider the AI search strategies for targeted lookup")
        
    except Exception as e:
        logger.error(f"Error during AI enhancement: {e}")


if __name__ == "__main__":
    # Note: Requires Ollama to be installed and running
    # Install: https://ollama.ai/
    # Run: ollama serve
    # Pull model: ollama pull llama3.1
    main()
