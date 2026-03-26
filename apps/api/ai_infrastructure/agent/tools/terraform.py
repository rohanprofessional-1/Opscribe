from langchain.tools import BaseTool, tool
import os

def get_terraform_generator_tool() -> BaseTool:
    """
    Tool that generates a .tf file and (eventually) commits it to the user's Github.
    """
    
    @tool(name="generate_terraform_file", return_direct=True)
    def generate_terraform_file(resource_type: str, resource_name: str, hcl_code: str, file_name: str) -> str:
        """
        Generates a HashiCorp Configuration Language (.tf) file for a specified resource.
        Inputs: 
        - resource_type: (e.g., 'aws_s3_bucket')
        - resource_name: (e.g., 'my-bucket')
        - hcl_code: The raw HCL code string.
        - file_name: The desired filename (e.g., 'main.tf')
        """
        # Phase 1: Just return the HCL to the user in a formatted Markdown block
        # Phase 2: Use the Github API (via opscribe ingestion token) to open a PR
        
        # Skeleton implementation:
        return f"Successfully generated Terraform file `{file_name}` for {resource_type}.\n\n```hcl\n{hcl_code}\n```\n\n*(Note: In the future, this will open a GitHub PR directly!)*"
        
    return generate_terraform_file
