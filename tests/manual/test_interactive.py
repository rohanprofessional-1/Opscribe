#!/usr/bin/env python3
"""
Interactive AWS Service Detection Tester

A simple CLI tool for students to explore AWS service detection.
Run this to interactively test different AWS services in your account.

Usage:
    python3 apps/api/test_interactive.py
"""

import asyncio
import sys
from apps.api.ingestors.aws.detector import AWSDetector


class Colors:
    """Terminal colors for prettier output"""
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_section(title):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.END}")


async def test_credentials():
    """Test if AWS credentials are configured correctly"""
    print_section("Testing AWS Credentials")
    
    try:
        detector = AWSDetector()
        account_id = detector._get_account_id()
        print_success(f"Connected to AWS Account: {account_id}")
        print_info(f"Region: {detector.region_name}")
        return True
    except Exception as e:
        print_error(f"Failed to connect: {str(e)}")
        print_info("Make sure your AWS credentials are configured correctly.")
        print_info("See the README for setup instructions.")
        return False


async def test_ec2(detector):
    """Test EC2 discovery"""
    print_section("Testing EC2 Discovery")
    
    try:
        nodes = detector._discover_ec2()
        print_success(f"Found {len(nodes)} EC2 instances")
        
        if nodes:
            print(f"\n{Colors.BOLD}Instances:{Colors.END}")
            for node in nodes:
                print(f"  • {node.display_name}")
                print(f"    Type: {node.properties.get('instance_type')}")
                print(f"    State: {node.properties.get('state')}")
                print(f"    IP: {node.properties.get('private_ip')}")
        else:
            print_info("No EC2 instances found in this account")
        
        return len(nodes)
    except Exception as e:
        print_error(f"EC2 discovery failed: {str(e)}")
        return 0


async def test_lambda(detector):
    """Test Lambda discovery"""
    print_section("Testing Lambda Discovery")
    
    try:
        nodes = detector._discover_lambda()
        print_success(f"Found {len(nodes)} Lambda functions")
        
        if nodes:
            print(f"\n{Colors.BOLD}Functions:{Colors.END}")
            for node in nodes[:5]:  # Show first 5
                print(f"  • {node.display_name}")
                print(f"    Runtime: {node.properties.get('runtime')}")
                print(f"    Memory: {node.properties.get('memory_size')} MB")
        else:
            print_info("No Lambda functions found in this account")
        
        return len(nodes)
    except Exception as e:
        print_error(f"Lambda discovery failed: {str(e)}")
        return 0


async def test_databases(detector):
    """Test database service discovery"""
    print_section("Testing Database Services")
    
    total = 0
    
    # RDS
    try:
        rds_nodes = detector._discover_rds()
        print_success(f"Found {len(rds_nodes)} RDS/Aurora instances")
        
        if rds_nodes:
            print(f"{Colors.BOLD}RDS Instances:{Colors.END}")
            for node in rds_nodes:
                print(f"  • {node.display_name}")
                print(f"    Engine: {node.properties.get('engine')}")
                print(f"    Status: {node.properties.get('status')}")
        
        total += len(rds_nodes)
    except Exception as e:
        print_error(f"RDS discovery failed: {str(e)}")
    
    print()
    
    # DynamoDB
    try:
        dynamo_nodes = detector._discover_dynamodb()
        print_success(f"Found {len(dynamo_nodes)} DynamoDB tables")
        
        if dynamo_nodes:
            print(f"{Colors.BOLD}DynamoDB Tables:{Colors.END}")
            for node in dynamo_nodes[:5]:  # Show first 5
                print(f"  • {node.display_name}")
                print(f"    Items: {node.properties.get('item_count')}")
        
        total += len(dynamo_nodes)
    except Exception as e:
        print_error(f"DynamoDB discovery failed: {str(e)}")
    
    print()
    
    # Redshift
    try:
        redshift_nodes = detector._discover_redshift()
        print_success(f"Found {len(redshift_nodes)} Redshift clusters")
        
        if redshift_nodes:
            print(f"{Colors.BOLD}Redshift Clusters:{Colors.END}")
            for node in redshift_nodes:
                print(f"  • {node.display_name}")
                print(f"    Nodes: {node.properties.get('number_of_nodes')}")
        
        total += len(redshift_nodes)
    except Exception as e:
        print_error(f"Redshift discovery failed: {str(e)}")
    
    return total


async def test_storage(detector):
    """Test storage service discovery"""
    print_section("Testing Storage Services")
    
    total = 0
    
    # S3
    try:
        s3_nodes = detector._discover_s3()
        print_success(f"Found {len(s3_nodes)} S3 buckets")
        
        if s3_nodes:
            print(f"{Colors.BOLD}S3 Buckets:{Colors.END}")
            for node in s3_nodes[:5]:  # Show first 5
                print(f"  • {node.display_name}")
        
        total += len(s3_nodes)
    except Exception as e:
        print_error(f"S3 discovery failed: {str(e)}")
    
    print()
    
    # EBS
    try:
        ebs_nodes = detector._discover_ebs()
        print_success(f"Found {len(ebs_nodes)} EBS volumes")
        
        if ebs_nodes:
            print(f"{Colors.BOLD}EBS Volumes:{Colors.END}")
            for node in ebs_nodes[:5]:  # Show first 5
                print(f"  • {node.display_name}")
                print(f"    Size: {node.properties.get('size')} GB")
        
        total += len(ebs_nodes)
    except Exception as e:
        print_error(f"EBS discovery failed: {str(e)}")
    
    print()
    
    # EFS
    try:
        efs_nodes = detector._discover_efs()
        print_success(f"Found {len(efs_nodes)} EFS file systems")
        total += len(efs_nodes)
    except Exception as e:
        print_error(f"EFS discovery failed: {str(e)}")
    
    return total


async def test_networking(detector):
    """Test networking service discovery"""
    print_section("Testing Networking Services")
    
    total = 0
    
    # VPC
    try:
        vpc_nodes = detector._discover_vpc()
        print_success(f"Found {len(vpc_nodes)} VPCs")
        
        if vpc_nodes:
            print(f"{Colors.BOLD}VPCs:{Colors.END}")
            for node in vpc_nodes:
                print(f"  • {node.display_name}")
                print(f"    CIDR: {node.properties.get('cidr_block')}")
        
        total += len(vpc_nodes)
    except Exception as e:
        print_error(f"VPC discovery failed: {str(e)}")
    
    print()
    
    # Load Balancers
    try:
        lb_nodes = detector._discover_load_balancers()
        print_success(f"Found {len(lb_nodes)} Load Balancers")
        
        if lb_nodes:
            print(f"{Colors.BOLD}Load Balancers:{Colors.END}")
            for node in lb_nodes:
                print(f"  • {node.display_name}")
                print(f"    Type: {node.properties.get('load_balancer_type')}")
        
        total += len(lb_nodes)
    except Exception as e:
        print_error(f"Load Balancer discovery failed: {str(e)}")
    
    print()
    
    # CloudFront
    try:
        cf_nodes = detector._discover_cloudfront()
        print_success(f"Found {len(cf_nodes)} CloudFront distributions")
        total += len(cf_nodes)
    except Exception as e:
        print_error(f"CloudFront discovery failed: {str(e)}")
    
    return total


async def test_security(detector):
    """Test security service discovery"""
    print_section("Testing Security Services")
    
    total = 0
    
    # IAM Roles
    try:
        iam_nodes = detector._discover_iam_roles()
        print_success(f"Found {len(iam_nodes)} IAM roles")
        
        if iam_nodes:
            print(f"{Colors.BOLD}IAM Roles (first 5):{Colors.END}")
            for node in iam_nodes[:5]:
                print(f"  • {node.display_name}")
        
        total += len(iam_nodes)
    except Exception as e:
        print_error(f"IAM discovery failed: {str(e)}")
    
    print()
    
    # KMS
    try:
        kms_nodes = detector._discover_kms()
        print_success(f"Found {len(kms_nodes)} KMS keys")
        total += len(kms_nodes)
    except Exception as e:
        print_error(f"KMS discovery failed: {str(e)}")
    
    print()
    
    # Secrets Manager
    try:
        secrets_nodes = detector._discover_secrets_manager()
        print_success(f"Found {len(secrets_nodes)} secrets")
        
        if secrets_nodes:
            print(f"{Colors.BOLD}Secrets (first 5):{Colors.END}")
            for node in secrets_nodes[:5]:
                print(f"  • {node.display_name}")
        
        total += len(secrets_nodes)
    except Exception as e:
        print_error(f"Secrets Manager discovery failed: {str(e)}")
    
    return total


async def test_integration(detector):
    """Test integration service discovery"""
    print_section("Testing Integration Services")
    
    total = 0
    
    # SQS
    try:
        sqs_nodes = detector._discover_sqs()
        print_success(f"Found {len(sqs_nodes)} SQS queues")
        total += len(sqs_nodes)
    except Exception as e:
        print_error(f"SQS discovery failed: {str(e)}")
    
    # SNS
    try:
        sns_nodes = detector._discover_sns()
        print_success(f"Found {len(sns_nodes)} SNS topics")
        total += len(sns_nodes)
    except Exception as e:
        print_error(f"SNS discovery failed: {str(e)}")
    
    # EventBridge
    try:
        eb_nodes = detector._discover_eventbridge()
        print_success(f"Found {len(eb_nodes)} EventBridge rules")
        total += len(eb_nodes)
    except Exception as e:
        print_error(f"EventBridge discovery failed: {str(e)}")
    
    # API Gateway
    try:
        api_nodes = detector._discover_api_gateway()
        print_success(f"Found {len(api_nodes)} API Gateway APIs")
        total += len(api_nodes)
    except Exception as e:
        print_error(f"API Gateway discovery failed: {str(e)}")
    
    return total


async def test_full_discovery(detector):
    """Run full discovery and show summary"""
    print_section("Running Full Discovery")
    
    try:
        result = await detector.discover()
        
        print_success(f"Discovery complete!")
        print(f"  Total resources found: {len(result.nodes)}")
        print(f"  Total relationships: {len(result.edges)}")
        
        # Group by service
        by_service = {}
        for node in result.nodes:
            service = node.properties.get("service", "Unknown")
            by_service[service] = by_service.get(service, 0) + 1
        
        print(f"\n{Colors.BOLD}Resources by Service:{Colors.END}")
        for service in sorted(by_service.keys()):
            count = by_service[service]
            print(f"  • {service}: {count}")
        
        return len(result.nodes)
    except Exception as e:
        print_error(f"Full discovery failed: {str(e)}")
        return 0


async def show_menu():
    """Display interactive menu"""
    print_section("AWS Service Detection Tester")
    
    print(f"{Colors.BOLD}What would you like to test?{Colors.END}\n")
    print("1. Test AWS credentials")
    print("2. Discover EC2 instances")
    print("3. Discover Lambda functions")
    print("4. Discover Database services (RDS, DynamoDB, Redshift)")
    print("5. Discover Storage services (S3, EBS, EFS)")
    print("6. Discover Networking services (VPC, ELB, CloudFront)")
    print("7. Discover Security services (IAM, KMS, Secrets)")
    print("8. Discover Integration services (SQS, SNS, EventBridge, API Gateway)")
    print("9. Run FULL DISCOVERY (all services)")
    print("0. Exit")
    print()


async def main():
    """Main interactive loop"""
    detector = None
    
    try:
        while True:
            await show_menu()
            
            try:
                choice = input(f"{Colors.BOLD}Enter your choice (0-9): {Colors.END}").strip()
            except EOFError:
                break
            
            if choice == "0":
                print("\n👋 Goodbye!\n")
                break
            
            elif choice == "1":
                if await test_credentials():
                    detector = AWSDetector()
            
            elif detector is None:
                print_error("Please test credentials first (option 1)")
            
            elif choice == "2":
                await test_ec2(detector)
            
            elif choice == "3":
                await test_lambda(detector)
            
            elif choice == "4":
                await test_databases(detector)
            
            elif choice == "5":
                await test_storage(detector)
            
            elif choice == "6":
                await test_networking(detector)
            
            elif choice == "7":
                await test_security(detector)
            
            elif choice == "8":
                await test_integration(detector)
            
            elif choice == "9":
                await test_full_discovery(detector)
            
            else:
                print_error("Invalid choice. Please try again.")
            
            input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.END}")
    
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.END}")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
