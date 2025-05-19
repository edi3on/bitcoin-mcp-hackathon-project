# bitcoin_utils.py
# Utility functions for working with Bitcoin blockchain data

import json
import logging
from typing import Dict, Any, List, Optional, Union
import time
from datetime import datetime

from bitcoin_connection import get_bitcoin_connection
from bitcoin_transactions import parse_kwargs

logger = logging.getLogger(__name__)

def get_blockchain_info() -> Dict[str, Any]:
    """
    Get information about the blockchain
    
    Returns:
        Dict with blockchain information
    """
    bitcoin = get_bitcoin_connection()
    return bitcoin.run_command(["getblockchaininfo"])

def get_network_info() -> Dict[str, Any]:
    """
    Get information about the network
    
    Returns:
        Dict with network information
    """
    bitcoin = get_bitcoin_connection()
    return bitcoin.run_command(["getnetworkinfo"])

def get_block(block_hash: str, verbose: int = 1) -> Dict[str, Any]:
    """
    Get block data
    
    Args:
        block_hash: Block hash
        verbose: Verbosity level (0-2)
            0: Returns a hex-encoded string
            1: Returns an object with block header and transaction IDs
            2: Returns an object with block header and transaction objects
            
    Returns:
        Block data
    """
    bitcoin = get_bitcoin_connection()
    return bitcoin.run_command(["getblock", block_hash, str(verbose)])

def get_block_hash(height: int) -> str:
    """
    Get block hash for a specific height
    
    Args:
        height: Block height
        
    Returns:
        Block hash
    """
    bitcoin = get_bitcoin_connection()
    result = bitcoin.run_command(["getblockhash", str(height)])
    
    # Handle different response formats
    if isinstance(result, dict):
        if "result" in result:
            return result["result"]
        if "error" in result:
            logger.error(f"Error getting block hash: {result['error']}")
            return json.dumps(result)
    
    return result

def estimate_smart_fee(conf_target: int, estimate_mode: str = "CONSERVATIVE") -> Dict[str, Any]:
    """
    Estimate fee rate needed for a transaction to confirm within a certain number of blocks
    
    Args:
        conf_target: Confirmation target in blocks
        estimate_mode: Fee estimate mode (UNSET, ECONOMICAL, CONSERVATIVE)
        
    Returns:
        Estimated fee rate
    """
    bitcoin = get_bitcoin_connection()
    return bitcoin.run_command(["estimatesmartfee", str(conf_target), estimate_mode])

