#!/usr/bin/env python3
"""
Simple script to test document ingestion pipeline.
Usage: python ingest_document.py <path_to_pdf>
"""

import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ingestion import PDFProcessor, ContextualUploader

console = Console()

def main():
    parser = argparse.ArgumentParser(description="Ingest a PDF document into Contextual AI")
    parser.add_argument("pdf_path", help="Path to the PDF file to ingest")
    parser.add_argument("--no-thinking", action="store_true", help="Don't display Gemini's thinking process")
    parser.add_argument("--skip-upload", action="store_true", help="Only process, don't upload to Contextual")
    
    args = parser.parse_args()
    
    # Validate PDF path
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        console.print(f"[red]Error: File not found: {pdf_path}[/red]")
        sys.exit(1)
    
    console.print(Panel.fit(
        f"[bold cyan]Document Ingestion Pipeline[/bold cyan]\n"
        f"File: {pdf_path.name}",
        border_style="cyan"
    ))
    
    try:
        # Step 1: Process PDF with Gemini
        console.print("\n[bold]Step 1: Processing with Gemini 2.5 Flash[/bold]")
        processor = PDFProcessor()
        content, metadata = processor.process_pdf(
            str(pdf_path), 
            display_thinking=not args.no_thinking
        )
        
        # Display extracted metadata
        console.print("\n[bold green]✓ Document processed successfully![/bold green]")
        
        table = Table(title="Document Metadata", show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        
        for key, value in metadata.items():
            if isinstance(value, list):
                value = ", ".join(value)
            table.add_row(key.title(), str(value))
        
        console.print(table)
        
        # Save extracted content to file
        output_dir = Path("extracted_texts")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{pdf_path.stem}_extracted.xml"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        console.print(f"\n[green]✓ Extracted text saved to:[/green] {output_file}")
        
        # Display content preview
        console.print(f"\n[bold]Content Preview:[/bold]")
        preview = content[:500] + "..." if len(content) > 500 else content
        console.print(Panel(preview, border_style="dim"))
        console.print(f"[dim]Total content length: {len(content)} characters[/dim]")
        
        if args.skip_upload:
            console.print("\n[yellow]Skipping upload to Contextual AI (--skip-upload flag)[/yellow]")
            return
        
        # Step 2: Upload to Contextual AI
        console.print("\n[bold]Step 2: Uploading to Contextual AI[/bold]")
        uploader = ContextualUploader()
        result = uploader.upload_document(content, metadata)
        
        console.print("\n[bold green]✓ Document successfully ingested![/bold green]")
        
        # Display upload result
        if "document_id" in result or "id" in result:
            doc_id = result.get("document_id", result.get("id"))
            console.print(f"[cyan]Document ID:[/cyan] {doc_id}")
        
    except Exception as e:
        console.print(f"\n[red]Error during ingestion:[/red] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()