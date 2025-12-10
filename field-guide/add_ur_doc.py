# field-guide/add_ur_doc.py

import os
import re

def get_multiline_input():
    """
    Helper function to allow the user to paste multiple lines of text.
    Stops reading when the user types 'DONE' on a new line.
    """
    print("\n--- PASTE YOUR TEXT BELOW ---")
    print("(Type 'DONE' on a new line and hit Enter when finished)")
    print("-----------------------------")
    
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == 'DONE':
                break
            lines.append(line)
        except EOFError:
            break
            
    return "\n".join(lines)

def create_html_file():
    print("Notion HTML Generator")
    print("---------------------")

    # --- Step 1: Get Category ---
    while True:
        print("\nChoose a category:")
        print("1. new-concepts")
        print("2. tutorials")
        choice = input("Enter 1 or 2: ").strip()
        
        if choice == "1":
            category = "new-concepts"
            break
        elif choice == "2":
            category = "tutorials"
            break
        else:
            print("Invalid choice. Please type 1 or 2.")

    # --- Step 2: Get Document Title ---
    title = input("\nEnter the Document Title (header inside Notion): ").strip()
    if not title:
        title = "Untitled Document"

    # --- Step 3: Get Filename ---
    filename = input("Enter the desired Filename (saved on disk): ").strip()
    if not filename:
        filename = "output_file"
    
    # Clean filename and ensure .html extension
    if not filename.endswith(".html"):
        filename += ".html"
    # Remove illegal characters for file systems
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)

    # --- Step 4: Get Content ---
    raw_text = get_multiline_input()

    if not raw_text.strip():
        print("\nError: No text provided. Aborting.")
        return

    # --- Step 5: Process and Save ---
    # Define paths
    base_dir = "docs"
    output_dir = os.path.join(base_dir, category)
    full_path = os.path.join(output_dir, filename)

    # Create directories if needed
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as error:
        print(f"Error creating directory: {error}")
        return

    # Convert text to HTML paragraphs
    paragraphs = raw_text.strip().split('\n\n')
    html_body = ""
    for p in paragraphs:
        clean_p = p.replace('\n', '<br>')
        html_body += f"<p>{clean_p}</p>\n"

    # HTML Template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
    </head>
    <body>
        <h1>{title}</h1>
        {html_body}
    </body>
    </html>
    """

    # Write file
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print("\n" + "-"*30)
        print("Success: File Created.")
        print(f"Location: {output_dir}")
        print(f"File:     {filename}")
        print("-"*30)
    except Exception as e:
        print(f"\nError occurred while writing the file: {e}")

if __name__ == "__main__":
    create_html_file()