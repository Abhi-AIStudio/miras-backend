#!/usr/bin/env python3
"""
Gemini-based validation module for checking and validating Contextual AI responses.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from google import genai
from google.genai import types
import os

from config import settings

class GeminiValidator:
    """Validate responses using Gemini."""
    
    def __init__(self):
        """Initialize Gemini client."""
        os.environ['GEMINI_API_KEY'] = settings.GEMINI_API_KEY
        self.client = genai.Client()
        self.model = settings.GEMINI_MODEL
        self.extracted_texts_dir = Path("extracted_texts")
    
    def validate_response_stream(
        self, 
        query: str, 
        response: str, 
        sources: Optional[List[Dict[str, Any]]] = None,
        use_full_document: bool = True
    ):
        """
        Stream validation with thinking process visible.
        Yields tuples of (type, content) where type is 'thought' or 'result'.
        """
        
        # Try to load the full extracted document if available
        full_document = None
        if use_full_document:
            full_document = self._load_extracted_document(sources)
        
        # Build validation prompt
        validation_prompt = f"""
        You are a fact-checking expert. Your job is simple:
        
        USER QUERY: {query}
        
        RESPONSE PROVIDED: {response}
        
        {f"FULL DOCUMENT FOR VERIFICATION:\n{full_document[:50000]}" if full_document else "FULL DOCUMENT NOT AVAILABLE"}
        
        Your tasks:
        1. Check if the query is answered: YES or NO
        2. Extract each factual claim from the response
        3. Verify each fact against the document: TRUE or FALSE
        
        For example, if response says "AUM is $3.8bn in May 2021", that's one fact to check.
        
        Return JSON with this structure:
        {{
            "query_answered": true/false,
            "facts_checked": [
                {{
                    "fact": "The exact factual claim from the response",
                    "verified": true/false,
                    "page_found": "page number if found, or null"
                }}
            ],
            "overall_accuracy": "percentage of facts that are true"
        }}
        
        Be generous - if a fact is essentially correct (e.g., $3.8bn vs $3,786mm), mark it TRUE.
        Focus on whether facts are correct, not on minor rounding or formatting differences.
        """
        
        thoughts = ""
        answer = ""
        
        # Stream Gemini's validation with thinking visible
        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=validation_prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=2048,  # Increased for better analysis
                    include_thoughts=True  # Include thought summaries
                ),
                response_mime_type="application/json"
            )
        ):
            for part in chunk.candidates[0].content.parts:
                if not part.text:
                    continue
                elif part.thought:
                    # Yield thought incrementally
                    thoughts += part.text
                    yield ("thought", part.text)
                else:
                    # Yield answer incrementally
                    answer += part.text
                    yield ("answer", part.text)
        
        # Parse the final JSON result
        try:
            result = json.loads(answer)
            facts = result.get("facts_checked", [])
            verified_count = sum(1 for f in facts if f.get("verified", False))
            total_facts = len(facts)
            
            # Calculate accuracy percentage
            accuracy = int((verified_count / total_facts * 100) if total_facts > 0 else 0)
            
            # Build compatible response
            final_result = {
                "query_answered": result.get("query_answered", False),
                "facts_checked": facts,
                "accuracy_score": accuracy,
                "verified_facts": verified_count,
                "total_facts": total_facts,
                "overall_accuracy": result.get("overall_accuracy", f"{accuracy}%")
            }
            
            yield ("result", final_result)
        except Exception as e:
            yield ("error", str(e))
    
    def validate_response(
        self, 
        query: str, 
        response: str, 
        sources: Optional[List[Dict[str, Any]]] = None,
        use_full_document: bool = True
    ) -> Dict[str, Any]:
        """
        Validate a response against the query and full document.
        
        Args:
            query: The original user query
            response: The response from Contextual AI
            sources: Optional list of source documents/references from Contextual
            use_full_document: Whether to load and use the full extracted XML document
            
        Returns:
            Validation result with accuracy score and issues
        """
        
        # Try to load the full extracted document if available
        full_document = None
        if use_full_document:
            full_document = self._load_extracted_document(sources)
        
        # Build validation prompt
        validation_prompt = f"""
        You are a fact-checking expert. Your job is simple:
        
        USER QUERY: {query}
        
        RESPONSE PROVIDED: {response}
        
        {f"FULL DOCUMENT FOR VERIFICATION:\n{full_document[:50000]}" if full_document else "FULL DOCUMENT NOT AVAILABLE"}
        
        Your tasks:
        1. Check if the query is answered: YES or NO
        2. Extract each factual claim from the response
        3. Verify each fact against the document: TRUE or FALSE
        
        For example, if response says "AUM is $3.8bn in May 2021", that's one fact to check.
        
        Return JSON with this structure:
        {{
            "query_answered": true/false,
            "facts_checked": [
                {{
                    "fact": "The exact factual claim from the response",
                    "verified": true/false,
                    "page_found": "page number if found, or null"
                }}
            ],
            "overall_accuracy": "percentage of facts that are true"
        }}
        
        Be generous - if a fact is essentially correct (e.g., $3.8bn vs $3,786mm), mark it TRUE.
        Focus on whether facts are correct, not on minor rounding or formatting differences.
        """
        
        # Get Gemini's validation
        response = self.client.models.generate_content(
            model=self.model,
            contents=validation_prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=1024  # Some thinking for analysis
                ),
                response_mime_type="application/json"
            )
        )
        
        try:
            result = json.loads(response.text)
            # Convert to old format for compatibility
            facts = result.get("facts_checked", [])
            verified_count = sum(1 for f in facts if f.get("verified", False))
            total_facts = len(facts)
            
            # Calculate accuracy percentage
            accuracy = int((verified_count / total_facts * 100) if total_facts > 0 else 0)
            
            # Build compatible response
            return {
                "query_answered": result.get("query_answered", False),
                "facts_checked": facts,
                "accuracy_score": accuracy,
                "verified_facts": verified_count,
                "total_facts": total_facts,
                "overall_accuracy": result.get("overall_accuracy", f"{accuracy}%")
            }
        except:
            return {
                "query_answered": False,
                "facts_checked": [],
                "accuracy_score": 0,
                "verified_facts": 0,
                "total_facts": 0,
                "overall_accuracy": "0%"
            }
    
    def _load_extracted_document(self, sources: Optional[List[Dict[str, Any]]]) -> Optional[str]:
        """
        Load the full extracted XML document based on the source references.
        
        Args:
            sources: Source references from Contextual (to identify the document)
            
        Returns:
            Full document content as string, or None if not found
        """
        # Try to identify the document from sources
        doc_name = None
        if sources and len(sources) > 0:
            # Get document name from first source
            first_source = sources[0]
            doc_name = first_source.get('doc_name', '')
            
            # Clean up the document name to match extracted file
            if doc_name:
                # Remove extension and clean up
                doc_name = doc_name.replace('.pdf', '').replace('.PDF', '')
        
        # If no document name from sources, try to find the most recent XML file
        if not doc_name:
            xml_files = list(self.extracted_texts_dir.glob("*.xml"))
            if xml_files:
                # Get the most recently modified XML file
                latest_file = max(xml_files, key=lambda p: p.stat().st_mtime)
                try:
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    print(f"Error loading {latest_file}: {e}")
                    return None
        
        # Try to find the extracted XML file
        possible_files = [
            self.extracted_texts_dir / f"{doc_name}_extracted.xml",
            self.extracted_texts_dir / f"{doc_name}.xml",
            # Try Steadview file specifically (since it's our main test doc)
            self.extracted_texts_dir / "Steadview Capital Partners LP_Investment Due Diligence_Jul-2021_Aksia (1)_extracted.xml"
        ]
        
        for file_path in possible_files:
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        print(f"Loaded full document from: {file_path.name}")
                        return content
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
        
        print(f"Could not find extracted document for: {doc_name}")
        return None
    
    def check_factual_accuracy(self, statement: str, context: str) -> Dict[str, Any]:
        """
        Check if a specific statement is factually accurate given context.
        
        Args:
            statement: The statement to check
            context: The context/source material
            
        Returns:
            Accuracy check result
        """
        
        prompt = f"""
        Check if this statement is factually accurate based on the given context:
        
        STATEMENT: {statement}
        
        CONTEXT: {context}
        
        Return JSON:
        {{
            "is_accurate": true/false,
            "confidence": 0-100,
            "explanation": "why it is or isn't accurate",
            "supporting_evidence": "quote from context if found"
        }}
        """
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json"
            )
        )
        
        try:
            return json.loads(response.text)
        except:
            return {
                "is_accurate": False,
                "confidence": 0,
                "explanation": "Could not validate",
                "supporting_evidence": ""
            }


# Simple test function
if __name__ == "__main__":
    import asyncio
    
    async def test_validation():
        validator = GeminiValidator()
        
        # Test with a sample query and response
        test_query = "What is the AUM of Steadview Capital?"
        test_response = "Steadview Capital has $2.7 billion in AUM as of May 2021."
        
        print("Testing Gemini Validation...")
        print(f"Query: {test_query}")
        print(f"Response: {test_response}")
        print("\nValidating...")
        
        result = validator.validate_response(test_query, test_response)
        
        print("\nValidation Result:")
        print(json.dumps(result, indent=2))
    
    asyncio.run(test_validation())