"""
SQL Generation Knowledge Base Chunker
Streamlined version with minimal redundancy and focused content
"""

import os
import re
import json
import sys
from typing import List, Dict, Any, Tuple, Optional, Union, Literal
from dataclasses import dataclass
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseChunk:
    """Represents a database-level chunk of documentation"""
    chunk_id: str
    chunk_type: Literal['database']
    content: str
    metadata: Dict[str, Any]

    def to_dict(self):
        metadata = dict(self.metadata)
        if 'chunk_type' not in metadata:
            metadata['chunk_type'] = self.chunk_type
        return {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'metadata': metadata
        }


@dataclass
class TableChunk:
    """Represents a table-level chunk of documentation"""
    chunk_id: str
    chunk_type: Literal['table']
    content: str
    metadata: Dict[str, Any]

    def to_dict(self):
        metadata = dict(self.metadata)
        if 'chunk_type' not in metadata:
            metadata['chunk_type'] = self.chunk_type
        return {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'metadata': metadata
        }


@dataclass
class ColumnChunk:
    """Represents a column-level chunk of documentation"""
    chunk_id: str
    chunk_type: Literal['column']
    content: str
    metadata: Dict[str, Any]

    def to_dict(self):
        # Ensure chunk_type is in metadata
        metadata = dict(self.metadata)
        if 'chunk_type' not in metadata:
            metadata['chunk_type'] = self.chunk_type
        return {
            'chunk_id': self.chunk_id,
            'content': self.content,
            'metadata': metadata
        }


class SQLKnowledgeBaseChunker:
    """
    Streamlined chunker for SQL database documentation.
    Creates three types of chunks with minimal redundancy:
    1. Database Chunks - Basic database information
    2. Table Chunks - Table name and purpose only
    3. Column Chunks - Detailed column information
    """
    
    def __init__(self):
        self.chunks = []
        self.parsing_errors = []
        
    def parse_markdown_file(self, file_path: str) -> List[Union['DatabaseChunk', 'TableChunk', 'ColumnChunk']]:
        """Parse a single markdown file and extract chunks"""
        logger.info(f"Parsing file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract basic info
            workbook, sheet = self._extract_file_info(content)
            
            # Parse database info
            db_info = self._parse_database_info(content)
            if not db_info:
                self.parsing_errors.append(f"Failed to parse database info from {file_path}")
                return []
            
            chunks = []

            # Parse tables first to include in database chunk
            tables = self._parse_tables(content)

            # Add database info chunk
            db_chunk = self._create_database_chunk(db_info, tables)
            chunks.append(db_chunk)
            
            for table in tables:
                # Add table summary chunk
                table_summary_chunk = self._create_table_summary_chunk(
                    table, db_info['db_name'], db_info.get('module_name', 'unknown'),
                    db_info.get('purpose', '')
                )
                chunks.append(table_summary_chunk)
                
                # Add table columns chunk
                table_columns_chunk = self._create_table_columns_chunk(
                    table, db_info['db_name'], db_info.get('module_name', 'unknown')
                )
                chunks.append(table_columns_chunk)
            
            logger.info(f"Created {len(chunks)} chunks from {file_path}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {str(e)}")
            self.parsing_errors.append(f"Error parsing {file_path}: {str(e)}")
            return []
    
    def _extract_file_info(self, content: str) -> Tuple[str, str]:
        """Extract workbook and sheet information"""
        workbook_match = re.search(r'# Workbook: (.+?)\.xlsx', content)
        sheet_match = re.search(r'## Sheet: (.+?)(?:\n|$)', content)
        
        workbook = workbook_match.group(1) if workbook_match else "Unknown"
        sheet = sheet_match.group(1) if sheet_match else "Unknown"
        
        return workbook, sheet
    
    def _parse_database_info(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse database information section"""
        db_info_pattern = r'### Database Info\n(.*?)(?=###|\Z)'
        db_info_match = re.search(db_info_pattern, content, re.DOTALL)
        
        if not db_info_match:
            return None
        
        db_info_text = db_info_match.group(1)
        
        # Extract fields using regex
        fields = {
            'system_name': r'- System Name:: (.+?)(?:\n|$)',
            'module_name': r'- Module Name:: (.+?)(?:\n|$)',
            'db_name': r'- Db Name:: (.+?)(?:\n|$)',
            'purpose': r'- Purpose:: (.+?)(?:\n|$)',
            'status': r'- Status:: (.+?)(?:\n|$)'
        }
        
        db_info = {}
        for key, pattern in fields.items():
            match = re.search(pattern, db_info_text, re.IGNORECASE)
            if match:
                db_info[key] = match.group(1).strip()
        
        # Ensure we have at least db_name
        if 'db_name' not in db_info:
            return None
            
        return db_info
    
    def _parse_tables(self, content: str) -> List[Dict[str, Any]]:
        """Parse all tables from the markdown content"""
        tables = []

        # Split content by table headers
        sections = re.split(r'(?=^### )', content, flags=re.MULTILINE)

        for section in sections:
            section = section.strip()
            if not section.startswith('### '):
                continue

            # Pattern to match individual table sections
            table_pattern = (
                r'^### ([^\n]+)\s*\n'
                r'\s*\|\s*Attribute\s*\|\s*Value\s*\|\s*\n'
                r'\s*\|\s*[-]+\s*\|\s*[-]+\s*\|\s*\n'
                r'\s*\|\s*Table Name\s*\|\s*([^\|]+)\s*\|\s*\n'
                r'\s*\|\s*Purpose\s*\|\s*([^\|]+)\s*\|\s*\n'
                r'\s*#### Columns\s*\n'
                r'(.*)'
            )

            match = re.search(table_pattern, section, re.DOTALL)
            if match:
                table_section_name = match.group(1).strip()
                table_name = match.group(2).strip()
                table_purpose = match.group(3).strip()
                columns_text = match.group(4).strip()

                # Skip invalid tables
                if not table_name:
                    continue

                # Parse columns
                columns = self._parse_columns(columns_text)

                tables.append({
                    'section_name': table_section_name,
                    'table_name': table_name,
                    'purpose': table_purpose,
                    'columns': columns,
                    'columns_text': columns_text
                })

        return tables
    
    def _parse_columns(self, columns_text: str) -> List[Dict[str, str]]:
        """Parse column information from column table"""
        columns = []
        
        # Pattern to match column rows - updated to capture all 6 fields
        column_pattern = r'\| ([^\|]+) \| ([^\|]+) \| ([^\|]*) \| ([^\|]*) \| ([^\|]*) \| ([^\|]*) \|'
        
        for match in re.finditer(column_pattern, columns_text):
            col_name = match.group(1).strip()
            data_type = match.group(2).strip()
            key = match.group(3).strip()
            null = match.group(4).strip()
            description = match.group(5).strip()
            category = match.group(6).strip()
            
            # Skip header row and separator lines
            if col_name in ('Column', '---') or col_name.strip().replace('-', '').replace(' ', '') == '':
                continue
            
            columns.append({
                'name': col_name,
                'data_type': data_type,
                'key': key,
                'null': null,
                'description': description,
                'category': category
            })
        
        return columns
    
    def _create_database_chunk(self, db_info: Dict[str, Any], tables: List[Dict[str, Any]]) -> DatabaseChunk:
        """Create streamlined database info chunk with table information for better semantic search"""
        # Create content with database info
        content_lines = [
            f"Database: {db_info.get('db_name', 'Unknown')}",
            f"System: {db_info.get('system_name', 'Unknown')}",
            f"Module: {db_info.get('module_name', 'Unknown')}",
            f"Purpose: {db_info.get('purpose', 'Unknown')}",
            ""
        ]

        # Add key table information
        if tables:
            content_lines.append("Key Tables:")
            for table in tables[:10]:  # Limit to first 10 tables
                table_name = table.get('table_name', 'Unknown')
                table_purpose = table.get('purpose', 'Unknown')
                content_lines.append(f"- {table_name}: {table_purpose}")

            if len(tables) > 10:
                content_lines.append(f"- ... and {len(tables) - 10} more tables")

        content = "\n".join(content_lines)
        
        # Create minimal metadata for filtering
        metadata = {
            'chunk_type': 'database',
            'database_name': db_info.get('db_name', 'Unknown'),
            'system_name': db_info.get('system_name', 'Unknown'),
            'module_name': db_info.get('module_name', 'Unknown')
        }

        # Add status if available
        if 'status' in db_info:
            metadata['status'] = db_info['status']
        
        # Generate chunk ID using :: as delimiter with module name
        db_name = db_info.get('db_name', 'unknown')
        module_name = db_info.get('module_name', 'unknown')
        chunk_id = f"database::{db_name}::{module_name}"
        
        return DatabaseChunk(
            chunk_id=chunk_id,
            chunk_type='database',
            content=content,
            metadata=metadata
        )
    
    def _create_table_summary_chunk(self, table: Dict[str, Any], db_name: str, module_name: str, db_purpose: str = "", primary_keys: List[str] = None, unique_keys: List[str] = None) -> TableChunk:
        """Create streamlined table summary chunk"""
        table_name = table['table_name']
        table_purpose = table['purpose']

        # Simple content - just table name and purpose
        content = f"Table: {table_name}\nPurpose: {table_purpose}"

        # Extract primary keys and unique keys from table columns
        columns = table.get('columns', [])
        if primary_keys is None:
            primary_keys = [c['name'] for c in columns if c.get('key','').upper() == 'PRI']
        if unique_keys is None:
            unique_keys = [c['name'] for c in columns if c.get('key','').upper() == 'UNI']

        # Minimal metadata for filtering
        metadata = {
            'chunk_type': 'table',
            'database_name': db_name,
            'database_purpose': db_purpose,
            'table_name': table_name,
            'module_name': module_name,
            'primary_keys': primary_keys,
            'unique_keys': unique_keys
        }
        
        # Generate chunk ID using :: as delimiter with module name
        chunk_id = f"table::{db_name}::{module_name}::{table_name}"
        
        return TableChunk(
            chunk_id=chunk_id,
            chunk_type='table',
            content=content,
            metadata=metadata
        )
    
    def _create_table_columns_chunk(self, table: Dict[str, Any], db_name: str, module_name: str) -> ColumnChunk:
        """Create streamlined table columns chunk"""
        table_name = table['table_name']
        table_purpose = table['purpose']
        columns = table['columns']

        # Create content with column details in readable format
        content_lines = [
            f"Table: {table_name}",
            f"Purpose: {table_purpose}",
            ""
        ]

        # Add column information in structured, readable format
        for col in columns:
            # Format: column_name data_type key null description category
            key = col.get('key', '').lower().strip()
            null = col.get('null', '').lower().strip()
            description = col.get('description', '').strip()
            category = col.get('category', '').lower().strip()

            # Build the column description line
            parts = [
                col['name'],
                col['data_type']
            ]

            if key:
                parts.append(key)
            if null:
                parts.append(null)
            if description:
                parts.append(description)
            if category:
                parts.append(category)

            col_line = " ".join(parts)
            content_lines.append(col_line)

        content = "\n".join(content_lines)
        
        # Extract useful metadata for SQL generation
        # primary_keys = [col['name'] for col in columns if 'PRI' in col.get('key', '')]
        primary_keys   = [c['name'] for c in columns if c.get('key','').upper() == 'PRI']
        unique_columns = [c['name'] for c in columns if c.get('key','').upper() == 'UNI']
        indexed_cols   = [c['name'] for c in columns if c.get('key','').upper() == 'MUL']

        
        # Metadata focused on what's needed for SQL generation
        metadata = {
            'chunk_type': 'column',
            'database_name': db_name,
            'table_name': table_name,
            'module_name': module_name,
            'column_names': [col['name'] for col in columns],
            'primary_keys': primary_keys,
            'unique_keys': unique_columns,
            'indexed_columns': indexed_cols
        }
        
        # Generate chunk ID using :: as delimiter with module name
        chunk_id = f"columns::{db_name}::{module_name}::{table_name}"
        
        return ColumnChunk(
            chunk_id=chunk_id,
            chunk_type='column',
            content=content,
            metadata=metadata
        )
    
    def process_directory(self, directory_path: str) -> List[Union['DatabaseChunk', 'TableChunk', 'ColumnChunk']]:
        """Process all markdown files in a directory (non-recursive)"""
        all_chunks = []
        
        for filename in os.listdir(directory_path):
            if filename.lower().endswith('.md'):
                file_path = os.path.join(directory_path, filename)
                chunks = self.parse_markdown_file(file_path)
                all_chunks.extend(chunks)
        
        return all_chunks
    
    def save_chunks_to_json(self, chunks: List[Union['DatabaseChunk', 'TableChunk', 'ColumnChunk']], output_path: str):
        """Save chunks to JSON file for inspection"""
        chunk_dicts = [chunk.to_dict() for chunk in chunks]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_dicts, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(chunks)} chunks to {output_path}")


def print_all_chunks(chunks: List[Union['DatabaseChunk', 'TableChunk', 'ColumnChunk']]):
    """Print all chunks in a detailed, readable format"""
    print("\n" + "="*80)
    print("STREAMLINED CHUNKS")
    print("="*80 + "\n")
    
    # Group chunks by type
    db_chunks = [c for c in chunks if c.chunk_type == 'database']
    table_chunks = [c for c in chunks if c.chunk_type == 'table']
    column_chunks = [c for c in chunks if c.chunk_type == 'column']
    
    # Print database chunks
    print(f"\n{'='*35} DATABASE CHUNKS ({len(db_chunks)}) {'='*35}")
    for i, chunk in enumerate(db_chunks, 1):
        print(f"\n--- Chunk {i} ---")
        print(f"Chunk ID: {chunk.chunk_id}")
        print(f"\nCONTENT:")
        print("-" * 60)
        print(chunk.content)
        print("-" * 60)
        print(f"\nMETADATA:")
        print(json.dumps(chunk.metadata, indent=2))
        print("\n" + "="*80)
    
    # Print table chunks
    print(f"\n{'='*35} TABLE CHUNKS ({len(table_chunks)}) {'='*35}")
    for i, chunk in enumerate(table_chunks, 1):
        print(f"\n--- Chunk {i} ---")
        print(f"Chunk ID: {chunk.chunk_id}")
        print(f"\nCONTENT:")
        print("-" * 60)
        print(chunk.content)
        print("-" * 60)
        print(f"\nMETADATA:")
        print(json.dumps(chunk.metadata, indent=2))
        print("\n" + "="*80)
    
    # Print column chunks
    print(f"\n{'='*35} COLUMN CHUNKS ({len(column_chunks)}) {'='*35}")
    for i, chunk in enumerate(column_chunks, 1):
        print(f"\n--- Chunk {i} ---")
        print(f"Chunk ID: {chunk.chunk_id}")
        print("\nCONTENT:")
        print("-" * 60)
        print(chunk.content)
        print("-" * 60)
        print("\nMETADATA:")
        print(json.dumps(chunk.metadata, indent=2))
        print("\n" + "="*80)


def main():
    """Main function to process markdown files or a directory of files"""
    parser = argparse.ArgumentParser(
        description="SQL KB Chunker - Parse markdown DB docs into structured chunks."
    )
    parser.add_argument("input_path", help="Path to a markdown file OR a folder containing .md files")
    parser.add_argument("output_dir", help="Folder where output JSON files will be saved")
    parser.add_argument(
        "--quiet", action="store_true",
        help="Do not print detailed chunks to stdout (useful when processing many files)"
    )
    args = parser.parse_args()

    input_path = args.input_path
    output_dir = args.output_dir
    quiet = args.quiet

    # Validate input path
    if not os.path.exists(input_path):
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    chunker = SQLKnowledgeBaseChunker()

    # If directory: process all .md files (non-recursive)
    if os.path.isdir(input_path):
        md_files = sorted(
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.lower().endswith(".md")
        )

        if not md_files:
            print(f"No .md files found in folder: {input_path}")
            sys.exit(1)

        total_chunks = 0
        processed_files = 0

        print(f"\nProcessing {len(md_files)} markdown files from: {input_path}")
        print("-" * 60)

        for fp in md_files:
            print(f"\nProcessing file: {fp}")
            print("-" * 60)
            chunks = chunker.parse_markdown_file(fp)

            if not chunks:
                print(f"No chunks were created from {fp}")
                continue

            if not quiet:
                print_all_chunks(chunks)

            base_name = os.path.splitext(os.path.basename(fp))[0]
            out_file = os.path.join(output_dir, f"{base_name}_chunks.json")
            chunker.save_chunks_to_json(chunks, out_file)

            processed_files += 1
            total_chunks += len(chunks)

        # Summary for directory processing
        print(f"\n{'='*35} SUMMARY {'='*35}")
        print(f"Files processed: {processed_files}/{len(md_files)}")
        print(f"Total chunks created: {total_chunks}")
        if chunker.parsing_errors:
            print(f"\n⚠️  Parsing errors encountered: {len(chunker.parsing_errors)}")
            for error in chunker.parsing_errors:
                print(f"  - {error}")

        sys.exit(0)

    # If single file:
    if os.path.isfile(input_path):
        print(f"\nProcessing file: {input_path}")
        print("-" * 60)
        chunks = chunker.parse_markdown_file(input_path)

        if not chunks:
            print(f"\nNo chunks were created from {input_path}")
            if chunker.parsing_errors:
                print("\nErrors encountered:")
                for error in chunker.parsing_errors:
                    print(f"  - {error}")
            sys.exit(1)

        if not quiet:
            print_all_chunks(chunks)

        base_name = os.path.splitext(os.path.basename(input_path))[0]
        json_output_file = os.path.join(output_dir, f"{base_name}_chunks.json")
        chunker.save_chunks_to_json(chunks, json_output_file)

        # Print summary
        print(f"\n{'='*35} SUMMARY {'='*35}")
        print(f"Total chunks created: {len(chunks)}")
        print(f"Database chunks: {len([c for c in chunks if c.chunk_type == 'database'])}")
        print(f"Table chunks: {len([c for c in chunks if c.chunk_type == 'table'])}")
        print(f"Column chunks: {len([c for c in chunks if c.chunk_type == 'column'])}")
        print(f"\nChunks saved to: {json_output_file}")
        
        if chunker.parsing_errors:
            print(f"\n⚠️  Parsing errors encountered: {len(chunker.parsing_errors)}")
            for error in chunker.parsing_errors:
                print(f"  - {error}")
        sys.exit(0)

    print(f"Error: Path is neither a file nor a directory: {input_path}")
    sys.exit(1)


if __name__ == "__main__":
    main()
