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
from urllib.parse import urlparse
from urllib.request import urlopen

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Ord wallet settings from environment variables
ORD_PATH = os.environ.get("ORD_PATH", "ord")  # Default to 'ord' in PATH
ORD_NETWORK = os.environ.get("ORD_NETWORK", "mainnet")  # Default to mainnet

def inscribe_ordinal(image_data: str, fee_rate: int = 15, ord_path: str = None, 
                    network: str = None, dry_run: bool = False) -> Dict[str, Any]:
    """
    Inscribe an image as a Bitcoin ordinal
    
    Args:
        image_data: Either a URL or base64-encoded image string
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
    
    # Validate network
    valid_networks = ['mainnet', 'testnet', 'signet']
    if network not in valid_networks:
        logger.error(f"Invalid network: {network}")
        return {"error": f"Invalid network. Must be one of: {', '.join(valid_networks)}"}
    
    # Validate fee rate
    if not isinstance(fee_rate, int) or fee_rate < 1:
        logger.error(f"Invalid fee rate: {fee_rate}")
        return {"error": "Invalid fee rate. Must be a positive integer."}
    
    try:
        # Create a temporary directory to store the image
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate a random filename
            file_name = f"{uuid.uuid4()}"
            
            # Determine if input is URL or base64
            is_url = False
            try:
                # Check if it's a valid URL
                parsed_url = urlparse(image_data)
                is_url = all([parsed_url.scheme, parsed_url.netloc])
            except:
                is_url = False
            
            # Full path to save the image
            file_path = None
            
            # Process based on input type
            if is_url:
                # If URL, determine extension from content type
                try:
                    with urlopen(image_data) as response:
                        content_type = response.info().get_content_type()
                        
                        # Map content type to extension
                        extension_map = {
                            'image/jpeg': '.jpg',
                            'image/png': '.png',
                            'image/gif': '.gif',
                            'image/webp': '.webp',
                            'image/svg+xml': '.svg'
                        }
                        
                        # Default to .png if content type not recognized
                        extension = extension_map.get(content_type, '.png')
                        file_path = os.path.join(temp_dir, file_name + extension)
                        
                        # Download the image
                        with open(file_path, 'wb') as f:
                            f.write(response.read())
                        
                        logger.info(f"Downloaded image from URL to {file_path}")
                except Exception as e:
                    logger.error(f"Error downloading image from URL: {str(e)}")
                    return {"error": f"Failed to download image from URL: {str(e)}"}
            else:
                # Assume it's base64 encoded
                try:
                    # Try to determine the file type from the base64 string
                    if "data:image/" in image_data:
                        # Extract the type from the data URL
                        image_type = image_data.split(';')[0].split('/')[1]
                        # Remove the data URL prefix
                        image_data = image_data.split(',')[1]
                    else:
                        # Default to PNG if we can't determine the type
                        image_type = "png"
                    
                    # Map the type to extension
                    extension_map = {
                        'jpeg': '.jpg',
                        'jpg': '.jpg',
                        'png': '.png',
                        'gif': '.gif',
                        'webp': '.webp',
                        'svg+xml': '.svg',
                        'svg': '.svg'
                    }
                    
                    extension = extension_map.get(image_type, '.png')
                    file_path = os.path.join(temp_dir, file_name + extension)
                    
                    # Decode and save the image
                    image_bytes = base64.b64decode(image_data)
                    with open(file_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    logger.info(f"Saved base64 image to {file_path}")
                except Exception as e:
                    logger.error(f"Error processing base64 image: {str(e)}")
                    return {"error": f"Failed to process base64 image: {str(e)}"}
            
            if not file_path or not os.path.exists(file_path):
                return {"error": "Failed to save image file"}
            
            # Build the command with appropriate network flag
            command = [ord_path]
            if network == "testnet":
                command.append("--testnet")
            elif network == "signet":
                command.append("--signet")
            
            # Add the wallet inscribe command with parameters
            command.extend(["wallet", "inscribe", "--fee-rate", str(fee_rate)])
            
            # Add dry-run if requested
            if dry_run:
                command.append("--dry-run")
                
            # Add the file path
            command.extend(["--file", file_path])
            
            # Execute the command
            logger.info(f"Executing ord command: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True)
            
            # Check for errors
            if result.returncode != 0:
                error_message = result.stderr.strip() if result.stderr else "unknown error"
                logger.error(f"Error in ord inscribe command: {error_message}")
                return {"error": f"Ord inscribe command failed: {error_message}", "command": ' '.join(command)}
            
            # Parse the output
            output = result.stdout.strip()
            
            # Log the successful inscription
            if not dry_run:
                logger.info(f"Ordinal inscription created via ord")
            else:
                logger.info(f"Dry run completed for ordinal inscription")
            
            # Return success response
            response = {
                "success": True,
                "network": network,
                "output": output,
                "dry_run": dry_run
            }
            
            # Try to extract inscription ID if available
            try:
                # Pattern may vary based on ord version
                import re
                inscription_match = re.search(r'inscription:?\s*([a-fA-F0-9]+i\d+)', output, re.IGNORECASE)
                if inscription_match:
                    response["inscription_id"] = inscription_match.group(1)
                
                # Try to extract the transaction ID
                txid_match = re.search(r'(txid:|transaction id:)\s*([a-fA-F0-9]{64})', output, re.IGNORECASE)
                if txid_match:
                    response["txid"] = txid_match.group(2)
            except Exception as e:
                logger.warning(f"Could not extract inscription ID: {str(e)}")
            
            return response
    
    except Exception as e:
        logger.error(f"Error inscribing ordinal: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Error inscribing ordinal: {str(e)}"}

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
                response["parsed"]["ordinal_balance_sats"] = float(ordinal_match.group(1))
            
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
