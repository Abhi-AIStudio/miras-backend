PROMPTS = {
    "document_extraction": """
    You are an expert document processor. Your task is to extract and preserve ALL content from this PDF document in XML format.
    
    Requirements:
    1. Extract ALL text content maintaining original structure
    2. Preserve table structures with proper XML tags
    3. Maintain heading hierarchies with appropriate XML nesting
    4. Preserve bullet points and numbered lists with list tags
    5. Extract image descriptions if images contain important information
    6. Use semantic XML tags that clearly indicate content type
    
    Output the extracted content in well-formed XML format following this structure:
    
    <document>
        <title>Document Title</title>
        <sections>
            <section level="1" title="Section Title">
                <content>Section content text</content>
                <subsection level="2" title="Subsection Title">
                    <content>Subsection content</content>
                    <list type="bullet">
                        <item>List item 1</item>
                        <item>List item 2</item>
                    </list>
                </subsection>
                <table>
                    <thead>
                        <row>
                            <cell>Header 1</cell>
                            <cell>Header 2</cell>
                        </row>
                    </thead>
                    <tbody>
                        <row>
                            <cell>Data 1</cell>
                            <cell>Data 2</cell>
                        </row>
                    </tbody>
                </table>
            </section>
        </sections>
    </document>
    
    Be thorough - extract ALL content without skipping or summarizing. Ensure proper XML escaping for special characters.
    """,
    
    "grounding_validation": """
    You are a fact-checking and validation expert. You have been given:
    1. The original user query
    2. The response generated from the knowledge base
    3. The source documents/references
    
    Your tasks:
    1. Fact-check the response against the source documents
    2. Identify any inaccuracies or hallucinations
    3. Determine if the user's query has been FULLY answered
    4. If not fully answered, identify what additional information is needed
    
    Output format:
    {
        "is_accurate": boolean,
        "accuracy_score": 0-100,
        "issues_found": ["list of any inaccuracies"],
        "query_fully_answered": boolean,
        "missing_information": ["what info is still needed"],
        "suggested_follow_up_queries": ["queries to get missing info"] or []
    }
    """,
    
    "metadata_extraction": """
    Extract the following metadata from this document:
    - Document title
    - Document type (report, manual, guide, etc.)
    - Key topics/subjects covered
    - Date (if available)
    - Author/Organization (if available)
    - Summary (2-3 sentences)
    
    Return as structured JSON.
    """
}