# bitcoin_wallet.py
# Utility module for wallet interactions with Bitcoin Core

import subprocess
import json
import logging
import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from bitcoin_connection import get_bitcoin_connection
import base64
import tempfile
import uuid
import shutil
from urllib.parse import urlparse
from urllib.request import urlopen

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Ord wallet settings from environment variables
ORD_PATH = os.environ.get("ORD_PATH", "ord")  # Default to 'ord' in PATH
ORD_NETWORK = os.environ.get("ORD_NETWORK", "mainnet")  # Default to mainnet

def inscribe_ordinal(data: str, fee_rate: int = 15, ord_path: str = None, 
                    network: str = None, dry_run: bool = False) -> Dict[str, Any]:
    """
    Inscribe arbitrary data as a Bitcoin ordinal.
    
    Args:
        data: Either a URL, base64-encoded data string, or a file path to the content to inscribe
        fee_rate: Fee rate in sat/vB (default: 15)
        ord_path: Path to ord executable (defaults to ORD_PATH env var or 'ord')
        network: Network to use ('mainnet', 'testnet', 'signet') (defaults to ORD_NETWORK env var or 'mainnet')
        dry_run: If true, don't sign or broadcast transaction (default: False)
        
    Returns:
        Dict containing inscription result information
    """
    # Use provided values or fall back to environment variables
    ord_path = ord_path or ORD_PATH
    network = network or ORD_NETWORK
    temp_dir = None
    created_temp_dir = False
    
    try:
        # Validate network
        valid_networks = ['mainnet', 'testnet', 'signet']
        if network not in valid_networks:
            logger.error(f"Invalid network: {network}")
            return {"error": f"Invalid network. Must be one of: {', '.join(valid_networks)}"}
        
        # Validate fee rate
        if not isinstance(fee_rate, int) or fee_rate < 1:
            logger.error(f"Invalid fee rate: {fee_rate}")
            return {"error": "Invalid fee rate. Must be a positive integer."}
        
        # Check if data is already a file path
        file_path = None
        if os.path.exists(data):
            file_path = data
            logger.info(f"Using provided file path: {file_path}")
        else:
            # Create temp directory for processing
            temp_dir = tempfile.mkdtemp()
            created_temp_dir = True
            
            # Determine if input is URL or base64
            is_url = False
            try:
                parsed_url = urlparse(data)
                is_url = all([parsed_url.scheme, parsed_url.netloc])
            except:
                is_url = False
            
            if is_url:
                # If URL, download the content
                try:
                    with urlopen(data) as response:
                        content_type = response.info().get_content_type()
                        
                        # Map content type to extension (expanded for broader support)
                        extension_map = {
                            'image/jpeg': '.jpg',
                            'image/png': '.png',
                            'image/gif': '.gif',
                            'image/webp': '.webp',
                            'image/svg+xml': '.svg',
                            'text/plain': '.txt',
                            'application/json': '.json',
                            'application/pdf': '.pdf',
                            'audio/mpeg': '.mp3',
                            'video/mp4': '.mp4'
                        }
                        
                        # Default to .bin for unknown types
                        extension = extension_map.get(content_type, '.bin')
                        file_name = f"{uuid.uuid4()}{extension}"
                        file_path = os.path.join(temp_dir, file_name)
                        
                        # Download the content
                        with open(file_path, 'wb') as f:
                            f.write(response.read())
                        
                        logger.info(f"Downloaded content from URL to {file_path}")
                except Exception as e:
                    logger.error(f"Error downloading content from URL: {str(e)}")
                    return {"error": f"Failed to download content from URL: {str(e)}"}
            else:
                # Assume it's a base64 encoded string
                try:
                    # Check for data URL format
                    base64_data = data
                    file_extension = "bin"  # Default for unknown data
                    
                    if "data:" in data:
                        # Extract MIME type from data URL
                        mime_part = data.split(';')[0].split(':')[1]
                        extension_map = {
                            'image/jpeg': 'jpg',
                            'image/png': 'png',
                            'image/gif': 'gif',
                            'image/webp': 'webp',
                            'image/svg+xml': 'svg',
                            'text/plain': 'txt',
                            'application/json': 'json',
                            'application/pdf': 'pdf',
                            'audio/mpeg': 'mp3',
                            'video/mp4': 'mp4'
                        }
                        file_extension = extension_map.get(mime_part, 'bin')
                        # Remove the data URL prefix
                        base64_data = data.split(',')[1]
                    
                    # Generate file path
                    file_name = f"{uuid.uuid4()}.{file_extension}"
                    file_path = os.path.join(temp_dir, file_name)
                    
                    # Decode and save the data
                    data_bytes = base64.b64decode(base64_data)
                    with open(file_path, 'wb') as f:
                        f.write(data_bytes)
                    
                    logger.info(f"Saved base64 data to {file_path}")
                except Exception as e:
                    logger.error(f"Error processing base64 data: {str(e)}")
                    return {"error": f"Failed to process base64 data: {str(e)}"}
        
        # Check if file exists
        if not file_path or not os.path.exists(file_path):
            return {"error": "Failed to obtain a valid file for inscription"}
            
        # Build inscription command
        command = [
            ord_path,
            f"--{network}",
            "wallet",
            "inscribe",
            "--fee-rate", str(fee_rate),
            "--file", file_path
        ]
        
        if dry_run:
            command.append("--dry-run")
        
        # Execute the command
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Check for errors
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            logger.error(f"Error inscribing ordinal: {error_msg}")
            return {
                "success": False,
                "error": f"Error inscribing ordinal: {error_msg}",
                "stderr": result.stderr,
                "command": " ".join(command)
            }
        
        # Parse the output
        output = result.stdout.strip()
        
        # Try to parse JSON response if possible
        inscription_data = {}
        try:
            # Check if output contains valid JSON
            if '{' in output and '}' in output:
                # Extract JSON part
                json_start = output.find('{')
                json_end = output.rfind('}') + 1
                json_part = output[json_start:json_end]
                
                inscription_data = json.loads(json_part)
            else:
                # If not JSON, parse the output lines
                lines = output.split('\n')
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        inscription_data[key.strip()] = value.strip()
        except json.JSONDecodeError:
            # If JSON parsing fails, store raw output
            inscription_data["raw_output"] = output
        
        # Return successful result
        result = {
            "success": True,
            "message": "Inscription successful" if not dry_run else "Dry run successful",
            "raw_output": output,
            "inscribed": not dry_run,
            "dry_run": dry_run,
            "network": network,
            "fee_rate": fee_rate
        }
        
        # Add parsed data if available
        if inscription_data:
            result["inscription_data"] = inscription_data
        
        if "inscription" in inscription_data:
            result["inscription_id"] = inscription_data["inscription"]
        
        return result
    
    except Exception as e:
        logger.error(f"Error creating ordinal inscription: {str(e)}")
        return {
            "success": False,
            "error": f"Error creating ordinal inscription: {str(e)}"
        }
    finally:
        # Clean up temporary directory if we created one
        if created_temp_dir and temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory {temp_dir}: {str(e)}")

def get_wallet_balance(ord_path: str = None, network: str = None) -> Dict[str, Any]:
    """
    Get the balance of the wallet using the ord command line tool
    
    Args:
        ord_path: Path to ord executable (defaults to ORD_PATH env var or 'ord')
        network: Network to use ('mainnet', 'testnet', 'signet') (defaults to ORD_NETWORK env var or 'mainnet')
        
    Returns:
        Dict containing wallet balance information
    """
    # Use provided values or fall back to environment variables
    ord_path = ord_path or ORD_PATH
    network = network or ORD_NETWORK
    
    # Validate network
    valid_networks = ['mainnet', 'testnet', 'signet']
    if network not in valid_networks:
        logger.error(f"Invalid network: {network}. Must be one of {valid_networks}")
        return {"error": f"Invalid network. Must be one of: {', '.join(valid_networks)}"}
    
    # Build the command with appropriate network flag
    command = [ord_path]
    if network == "testnet":
        command.append("--testnet")
    elif network == "signet":
        command.append("--signet")
    
    # Add the wallet balance command
    command.extend(["wallet", "balance"])
    
    logger.info(f"Executing ord command: {' '.join(command)}")
    try:
        # Execute the command
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Check for errors
        if result.returncode != 0:
            error_message = result.stderr.strip() if result.stderr else "unknown error"
            logger.error(f"Error in ord command: {error_message}")
            return {"error": f"Ord command failed: {error_message}", "command": ' '.join(command)}
        
        # Process the output
        output = result.stdout.strip()
        
        # Create a structured response
        # Ord typically returns balance in a format like: "xyz sat"
        # Parse it into a structured format
        try:
            import re
            
            # Look for patterns like "123 sat" or "123.45 sats"
            balance_match = re.search(r'(\d+(?:\.\d+)?)\s+sat', output)
            cardinal_match = re.search(r'cardinal:\s*(\d+(?:\.\d+)?)\s+sat', output, re.IGNORECASE)
            ordinal_match = re.search(r'ordinal:\s*(\d+(?:\.\d+)?)\s+sat', output, re.IGNORECASE)
            
            response = {
                "success": True,
                "network": network,
                "raw_output": output,
                "parsed": {}
            }
            
            # Extract the values if matches found
            if balance_match:
                response["parsed"]["total_balance_sats"] = float(balance_match.group(1))
            
            if cardinal_match:
                response["parsed"]["cardinal_balance_sats"] = float(cardinal_match.group(1))
                
            if ordinal_match:
                response["parsed"]["ordinal_balance_sats"] = float(cardinal_match.group(1))
            
            # Convert to BTC for convenience
            if "total_balance_sats" in response["parsed"]:
                response["parsed"]["total_balance_btc"] = response["parsed"]["total_balance_sats"] / 100000000
                
            return response
            
        except Exception as parse_error:
            # If parsing fails, just return the raw output
            logger.warning(f"Failed to parse ord balance output: {str(parse_error)}")
            return {
                "success": True,
                "network": network,
                "raw_output": output,
                "parse_error": str(parse_error)
            }
            
    except Exception as e:
        logger.error(f"Error getting wallet balance: {str(e)}")
        return {"error": f"Error getting wallet balance: {str(e)}"}

def get_wallet_transactions(ord_path: str = None, network: str = None, limit: int = None) -> Dict[str, Any]:
    """
    Get transaction history from the ord wallet.
    
    Args:
        ord_path: Path to ord executable (defaults to ORD_PATH env var or 'ord')
        network: Network to use ('mainnet', 'testnet', 'signet') (defaults to ORD_NETWORK env var or 'mainnet')
        limit: Maximum number of transactions to return (default: None, returns all)
        
    Returns:
        Dict containing wallet transaction history
    """
    # Use provided values or fall back to environment variables
    ord_path = ord_path or ORD_PATH
    network = network or ORD_NETWORK
    
    # Validate network
    valid_networks = ['mainnet', 'testnet', 'signet']
    if network not in valid_networks:
        logger.error(f"Invalid network: {network}. Must be one of {valid_networks}")
        return {"error": f"Invalid network. Must be one of: {', '.join(valid_networks)}"}
    
    # Validate limit if provided
    if limit is not None and (not isinstance(limit, int) or limit <= 0):
        logger.error(f"Invalid limit: {limit}. Must be a positive integer.")
        return {"error": "Invalid limit. Must be a positive integer."}
    
    # Build the command with appropriate network flag
    command = [ord_path]
    if network == "testnet":
        command.append("--testnet")
    elif network == "signet":
        command.append("--signet")
    
    # Add the wallet transactions command
    command.extend(["wallet", "transactions"])
    
    logger.info(f"Executing ord command: {' '.join(command)}")
    try:
        # Execute the command
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Check for errors
        if result.returncode != 0:
            error_message = result.stderr.strip() if result.stderr else "unknown error"
            logger.error(f"Error in ord command: {error_message}")
            return {"error": f"Ord command failed: {error_message}", "command": ' '.join(command)}
        
        # Process the output
        output = result.stdout.strip()
        
        # Try to parse the output as JSON if possible
        # Ord typically returns transactions in JSON format
        try:
            transactions = json.loads(output)
            
            # Apply limit if specified
            if limit is not None and isinstance(transactions, list):
                transactions = transactions[:limit]
                
            response = {
                "success": True,
                "network": network,
                "transactions": transactions,
                "count": len(transactions) if isinstance(transactions, list) else 1
            }
        except json.JSONDecodeError:
            # If not valid JSON, return as raw text
            response = {
                "success": True,
                "network": network,
                "raw_output": output,
                "parsing_note": "Output could not be parsed as JSON"
            }
            
            # If limit is specified, try to limit the output
            if limit is not None:
                import re
                # Try to split by transaction entries (this is a guess and might need adjustment)
                transactions = re.split(r'\n\s*\n', output)
                if len(transactions) > limit:
                    limited_output = '\n\n'.join(transactions[:limit])
                    response["raw_output"] = limited_output
                    response["truncated"] = True
                    response["total_transactions"] = len(transactions)
        
        return response
            
    except Exception as e:
        logger.error(f"Error getting wallet transactions: {str(e)}")
        return {"error": f"Error getting wallet transactions: {str(e)}"}

def send_from_wallet(address: str, amount_sats: int, ord_path: str = None, 
                     network: str = None, fee_rate: int = 1, dry_run: bool = False) -> Dict[str, Any]:
    """
    Send Bitcoin from the ord wallet to a specified address
    
    Args:
        address: The Bitcoin address to send to
        amount_sats: Amount to send in satoshis (integer)
        ord_path: Path to ord executable (defaults to ORD_PATH env var or 'ord')
        network: Network to use ('mainnet', 'testnet', 'signet') (defaults to ORD_NETWORK env var or 'mainnet')
        fee_rate: Fee rate in sat/vB (default: 1)
        dry_run: If true, don't sign or broadcast transaction (default: False)
        
    Returns:
        Dict containing transaction result information
    """
    # Use provided values or fall back to environment variables
    ord_path = ord_path or ORD_PATH
    network = network or ORD_NETWORK
    
    # Validate inputs
    if not address or not isinstance(address, str):
        logger.error("Invalid address provided")
        return {"error": "Invalid address. Must provide a valid Bitcoin address."}
        
    if not isinstance(amount_sats, int) or amount_sats <= 0:
        logger.error(f"Invalid amount: {amount_sats}")
        return {"error": "Invalid amount. Must be a positive integer in satoshis."}
    
    # A reasonable upper limit to prevent major mistakes (e.g. 100000000 sats = 1 BTC)
    if amount_sats > 100000000:
        logger.error(f"Amount exceeds safety limit: {amount_sats}")
        return {
            "error": "Amount exceeds safety limit of 1 BTC (100,000,000 sats). For security, this tool is limited to smaller transactions."
        }
        
    # Validate fee rate
    if not isinstance(fee_rate, int) or fee_rate < 1:
        logger.error(f"Invalid fee rate: {fee_rate}")
        return {"error": "Invalid fee rate. Must be a positive integer."}
    
    # Validate network
    valid_networks = ['mainnet', 'testnet', 'signet']
    if network not in valid_networks:
        logger.error(f"Invalid network: {network}")
        return {"error": f"Invalid network. Must be one of: {', '.join(valid_networks)}"}
    
    # Build the appropriate amount format (format is: amount followed by "sat")
    amount_str = f"{amount_sats}sat"
    
    # Build the command with appropriate network flag
    command = [ord_path]
    if network == "testnet":
        command.append("--testnet")
    elif network == "signet":
        command.append("--signet")
    
    # Add the wallet send command with parameters
    command.extend(["wallet", "send", "--fee-rate", str(fee_rate)])
    
    # Add dry-run if requested
    if dry_run:
        command.append("--dry-run")
        
    # Add the address and amount
    command.extend([address, amount_str])
    
    # Execute the command
    logger.info(f"Executing ord command: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Check for errors
        if result.returncode != 0:
            error_message = result.stderr.strip() if result.stderr else "unknown error"
            logger.error(f"Error in ord command: {error_message}")
            return {"error": f"Ord command failed: {error_message}", "command": ' '.join(command)}
        
        # Parse the output
        output = result.stdout.strip()
        
        # Log the successful transaction
        if not dry_run:
            logger.info(f"Bitcoin sent via ord: {amount_sats} sats to {address}")
        else:
            logger.info(f"Dry run completed for sending {amount_sats} sats to {address}")
        
        # Return success response
        response = {
            "success": True,
            "address": address,
            "amount_sats": amount_sats,
            "network": network,
            "output": output,
            "dry_run": dry_run
        }
        
        # If we can extract a txid from the output, include it
        if "txid:" in output.lower() or "transaction id:" in output.lower():
            # Simple extraction - might need refinement based on exact ord output format
            import re
            txid_match = re.search(r'(txid:|transaction id:)\s*([a-fA-F0-9]{64})', output, re.IGNORECASE)
            if txid_match:
                response["txid"] = txid_match.group(2)
        
        return response
        
    except Exception as e:
        logger.error(f"Error sending from wallet: {str(e)}")
        return {"error": f"Error sending Bitcoin: {str(e)}"}