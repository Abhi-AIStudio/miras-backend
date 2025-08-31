import os
import pathlib
from typing import Dict, Any, Optional, Tuple
from google import genai
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import settings, PROMPTS

console = Console()

class PDFProcessor:
    """Process PDFs using Gemini 2.5 Flash with thinking mode."""
    
    def __init__(self):
        """Initialize the PDF processor with Gemini client."""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Set API key as environment variable for auto-pickup
        os.environ['GEMINI_API_KEY'] = settings.GEMINI_API_KEY
        self.client = genai.Client()
        self.model = settings.GEMINI_MODEL
        
    def process_pdf(self, pdf_path: str, display_thinking: bool = True) -> Tuple[str, Dict[str, Any]]:
        """
        Process a PDF document using Gemini with thinking mode.
        
        Args:
            pdf_path: Path to the PDF file
            display_thinking: Whether to display thinking process to user
            
        Returns:
            Tuple of (extracted_content, metadata)
        """
        console.print(f"\n[bold cyan]Processing PDF:[/bold cyan] {pdf_path}")
        
        # Verify file exists and is a PDF
        file_path = pathlib.Path(pdf_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if file_path.suffix.lower() != '.pdf':
            raise ValueError(f"File is not a PDF: {pdf_path}")
        
        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        console.print(f"[dim]File size: {file_size_mb:.2f} MB[/dim]")
        
        if file_size_mb > settings.MAX_PDF_SIZE_MB:
            raise ValueError(f"PDF size exceeds maximum of {settings.MAX_PDF_SIZE_MB} MB")
        
        # Process based on file size
        if file_size_mb > 20:
            console.print("[yellow]Large file detected, using File API...[/yellow]")
            content, metadata = self._process_large_pdf(file_path, display_thinking)
        else:
            content, metadata = self._process_inline_pdf(file_path, display_thinking)
        
        return content, metadata
    
    def _process_inline_pdf(self, file_path: pathlib.Path, display_thinking: bool) -> Tuple[str, Dict[str, Any]]:
        """Process PDF under 20MB using inline upload."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Extract content with thinking
            task = progress.add_task("Extracting document content...", total=None)
            
            thoughts_summary = ""
            extracted_content = ""
            
            # Stream the response to get thinking process
            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=[
                    types.Part.from_bytes(
                        data=file_path.read_bytes(),
                        mime_type='application/pdf'
                    ),
                    PROMPTS["document_extraction"]
                ],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=settings.GEMINI_THINKING_BUDGET,
                        include_thoughts=True
                    )
                )
            ):
                for part in chunk.candidates[0].content.parts:
                    if not part.text:
                        continue
                    elif part.thought:
                        thoughts_summary += part.text
                        if display_thinking:
                            # Display thinking in real-time (show full text, no truncation)
                            progress.update(task, description=f"[yellow]Thinking:[/yellow] {part.text}")
                    else:
                        extracted_content += part.text
            
            progress.update(task, description="[green]Content extraction complete![/green]")
        
        # Display full thinking summary if enabled
        if display_thinking and thoughts_summary:
            # Save thinking to file for full review
            thinking_dir = pathlib.Path("extracted_texts")
            thinking_dir.mkdir(exist_ok=True)
            thinking_file = thinking_dir / f"{file_path.stem}_thinking.txt"
            with open(thinking_file, "w", encoding="utf-8") as f:
                f.write(thoughts_summary)
            
            # Display in panel (might be truncated if very long)
            console.print(Panel(
                thoughts_summary[:5000] + "..." if len(thoughts_summary) > 5000 else thoughts_summary,
                title="[bold yellow]Gemini's Thinking Process[/bold yellow]",
                border_style="yellow"
            ))
            console.print(f"[dim]Full thinking saved to: {thinking_file}[/dim]")
        
        # Extract metadata
        console.print("\n[cyan]Extracting metadata...[/cyan]")
        metadata = self._extract_metadata(file_path)
        
        return extracted_content, metadata
    
    def _process_large_pdf(self, file_path: pathlib.Path, display_thinking: bool) -> Tuple[str, Dict[str, Any]]:
        """Process PDF over 20MB using File API."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Upload file
            upload_task = progress.add_task("Uploading PDF to Gemini File API...", total=None)
            
            uploaded_file = self.client.files.upload(
                file=file_path,
                config=dict(mime_type='application/pdf')
            )
            
            progress.update(upload_task, description=f"[green]Upload complete![/green] File ID: {uploaded_file.name}")
            
            # Extract content with thinking
            extract_task = progress.add_task("Extracting document content...", total=None)
            
            thoughts_summary = ""
            extracted_content = ""
            
            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=[uploaded_file, PROMPTS["document_extraction"]],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=settings.GEMINI_THINKING_BUDGET,
                        include_thoughts=True
                    )
                )
            ):
                for part in chunk.candidates[0].content.parts:
                    if not part.text:
                        continue
                    elif part.thought:
                        thoughts_summary += part.text
                        if display_thinking:
                            # Display thinking in real-time (show full text, no truncation)
                            progress.update(extract_task, description=f"[yellow]Thinking:[/yellow] {part.text}")
                    else:
                        extracted_content += part.text
            
            progress.update(extract_task, description="[green]Content extraction complete![/green]")
        
        # Display full thinking summary
        if display_thinking and thoughts_summary:
            # Save thinking to file for full review
            thinking_dir = pathlib.Path("extracted_texts")
            thinking_dir.mkdir(exist_ok=True)
            thinking_file = thinking_dir / f"{file_path.stem}_thinking.txt"
            with open(thinking_file, "w", encoding="utf-8") as f:
                f.write(thoughts_summary)
            
            # Display in panel (might be truncated if very long)
            console.print(Panel(
                thoughts_summary[:5000] + "..." if len(thoughts_summary) > 5000 else thoughts_summary,
                title="[bold yellow]Gemini's Thinking Process[/bold yellow]",
                border_style="yellow"
            ))
            console.print(f"[dim]Full thinking saved to: {thinking_file}[/dim]")
        
        # Extract metadata
        console.print("\n[cyan]Extracting metadata...[/cyan]")
        metadata = self._extract_metadata(file_path)
        
        # Clean up uploaded file (optional, auto-deleted after 48 hours)
        try:
            self.client.files.delete(name=uploaded_file.name)
            console.print("[dim]Cleaned up temporary file from Gemini[/dim]")
        except:
            pass  # File cleanup is optional
        
        return extracted_content, metadata
    
    def _extract_metadata(self, file_path: pathlib.Path) -> Dict[str, Any]:
        """Extract metadata from the PDF."""
        import json
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(
                    data=file_path.read_bytes(),
                    mime_type='application/pdf'
                ),
                PROMPTS["metadata_extraction"]
            ],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0  # No thinking needed for metadata
                ),
                response_mime_type="application/json"
            )
        )
        
        try:
            metadata = json.loads(response.text)
        except:
            metadata = {
                "title": file_path.stem,
                "type": "unknown",
                "topics": [],
                "summary": "Could not extract metadata"
            }
        
        metadata["filename"] = file_path.name
        metadata["size_mb"] = file_path.stat().st_size / (1024 * 1024)
        
        return metadata