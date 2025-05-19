# bitcoin_mcp_server.py
# Main entry point for the Bitcoin MCP server that interfaces with bitcoin-cli

import logging
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any
from urllib.parse import urlparse
from PIL import Image, UnidentifiedImageError

from mcp.server.fastmcp import FastMCP, Context
from bitcoin_connection import get_bitcoin_connection
from bitcoin_wallet import get_wallet_balance
from bitcoin_wallet import get_wallet_transactions, send_from_wallet
from bitcoin_wallet import inscribe_ordinal

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BitcoinMCPServer")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    try:
        logger.info("Bitcoin MCP server starting up")
        # Test bitcoin-cli connection on startup
        try:
            bitcoin = get_bitcoin_connection()
            if bitcoin.test_connection():
                connection_info = bitcoin.get_connection_info()
                logger.info(f"Successfully connected to Bitcoin Core")
                logger.info(f"  Network: {connection_info.get('chain', 'unknown')}")
                logger.info(f"  Blocks: {connection_info.get('blocks', 0)}")
                logger.info(f"  Version: {connection_info.get('version', 'unknown')} ({connection_info.get('subversion', '')})")
            else:
                logger.warning("Could not connect to Bitcoin Core on startup")
                logger.warning("Make sure Bitcoin Core is running and bitcoin-cli is available")
        except Exception as e:
            logger.warning(f"Could not connect to Bitcoin Core on startup: {str(e)}")
            logger.warning("Make sure Bitcoin Core is running and bitcoin-cli is available")
        yield {}
    finally:
        logger.info("Bitcoin MCP server shut down")

# Create the MCP server with lifespan support
mcp = FastMCP(
    "BitcoinMCP",
    description="Bitcoin Core integration through the Model Context Protocol",
    lifespan=server_lifespan
)

# Register Bitcoin Blockchain RPC tools
@mcp.tool()
def get_blockchain_info(ctx: Context) -> str:
    """
    Get information about the current state of the blockchain and network.
    
    Returns a JSON object with details about the current blockchain state including:
    chain, blocks, headers, bestblockhash, difficulty, mediantime, verificationprogress,
    pruned (if applicable), and other blockchain metrics.
    """
    try:
        from bitcoin_utils import get_blockchain_info
        result = get_blockchain_info()
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_blockchain_info: {str(e)}")
        return f"Error getting blockchain info: {str(e)}"

@mcp.tool()
def get_block_hash(ctx: Context, height: int) -> str:
    """
    Get the block hash for a specific block height.
    
    Parameters:
    - height: Block height to get the hash for. Block height only increases as more blocks are mined.
    
    Returns the block hash as a hex string.
    """
    try:
        from bitcoin_utils import get_block_hash
        result = get_block_hash(height)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_block_hash: {str(e)}")
        return f"Error getting block hash: {str(e)}"

@mcp.tool()
def get_block(ctx: Context, blockhash: str, verbosity: int = 1) -> str:
    """
    Get block data for a specific block hash.
    
    Parameters:
    - blockhash: The hash of the block to get
    - verbosity: The verbosity level (0-2, default=1)
      0: Returns a hex-encoded string of the block
      1: Returns an object with block header and transaction IDs
      2: Returns an object with block header and complete transaction objects
    
    Returns block data based on the specified verbosity level.
    """
    try:
        from bitcoin_utils import get_block
        result = get_block(blockhash, verbosity)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_block: {str(e)}")
        return f"Error getting block: {str(e)}"

@mcp.tool()
def estimate_smart_fee(ctx: Context, conf_target: int, estimate_mode: str = "CONSERVATIVE") -> str:
    """
    Estimate the fee rate needed for a transaction to be confirmed within a certain number of blocks.
    
    Parameters:
    - conf_target: Number of blocks to aim for confirmation
    - estimate_mode: Fee estimate mode (UNSET, ECONOMICAL, CONSERVATIVE) - default: CONSERVATIVE
    
    Returns an estimate of the fee rate (in BTC/kB) needed for a transaction 
    to be confirmed within conf_target blocks.
    """
    try:
        from bitcoin_utils import estimate_smart_fee
        result = estimate_smart_fee(conf_target, estimate_mode)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in estimate_smart_fee: {str(e)}")
        return f"Error estimating smart fee: {str(e)}"

@mcp.tool()
def get_network_info(ctx: Context) -> str:
    """
    Get information about the node's network connections and settings.
    
    Returns information about the node's connection to the network, including
    version, protocol version, timeoffset, connections count, and other network-related settings.
    """
    try:
        from bitcoin_utils import get_network_info
        result = get_network_info()
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_network_info: {str(e)}")
        return f"Error getting network info: {str(e)}"

@mcp.tool()
def get_wallet_balance_tool(ctx: Context) -> str:
    """
    Get the current balance of your Bitcoin wallet.
    
    Returns:
    A JSON object with wallet balance information including the total balance in satoshis.
    """
    try:
        result = get_wallet_balance()
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_wallet_balance_tool: {str(e)}")
        return f"Error getting wallet balance: {str(e)}"

@mcp.tool()
def wallet_send_bitcoin(ctx: Context, address: str, amount_sats: int, fee_rate: int = 1, confirm: bool = False) -> str:
    """
    Send Bitcoin from your wallet to a specified address, with fee confirmation.
    If confirm is False, does a dry run and returns the fee estimate and a prompt for confirmation.
    If confirm is True, sends the transaction for real.
    """
    try:
        if not confirm:
            # Dry run for fee estimate
            result = send_from_wallet(
                address=address,
                amount_sats=amount_sats,
                fee_rate=fee_rate,
                dry_run=True
            )
            # Extract fee info from result['output'] or result['raw_output']
            fee_info = result.get("output", "")
            return json.dumps({
                "confirmation_required": True,
                "fee_estimate": fee_info,
                "message": "This transaction will cost the above fee. Call this tool again with confirm=True to proceed."
            }, indent=2)
        else:
            # Real transaction
            result = send_from_wallet(
                address=address,
                amount_sats=amount_sats,
                fee_rate=fee_rate,
                dry_run=False
            )
            return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in wallet_send_bitcoin: {str(e)}")
        return json.dumps({"error": f"Error sending Bitcoin: {str(e)}"})

@mcp.tool()
def wallet_get_transactions(ctx: Context, limit: int = None) -> str:
    """
    Get transaction history from your wallet.
    
    Parameters:
    - limit: Maximum number of transactions to return (default: None, returns all)
    
    Returns a JSON object with your wallet transaction history.
    """
    try:
        result = get_wallet_transactions(limit=limit)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in wallet_get_transactions: {str(e)}")
        return json.dumps({"error": f"Error getting wallet transactions: {str(e)}"})

@mcp.tool()
def wallet_inscribe_ordinal(
    ctx: Context,
    data: str,
    fee_rate: int = 15,
    confirm: bool = False,
    is_image: bool = False,
    dry_run: bool = None
) -> str:
    """
    Inscribe arbitrary data as a Bitcoin ordinal, with optional image validation and fee confirmation.

    Parameters:
    - data: Either a URL pointing to the content, a base64-encoded data string, a file path, or plain text (which will be base64-encoded as text/plain)
    - fee_rate: Fee rate in sat/vB (default: 15)
    - confirm: If False, does a dry run and returns the fee estimate and a prompt for confirmation. If True, inscribes for real.
    - is_image: If true, validates that the input is a valid image (PNG, JPEG, GIF, WebP, or SVG) (default: False)

    Returns a JSON object with the inscription details and status.
    """
    import os
    import base64
    from urllib.parse import urlparse
    from PIL import Image, UnidentifiedImageError

    try:
        # Check if data is a URL, file path, or base64 data URL
        is_url = False
        try:
            parsed_url = urlparse(data)
            is_url = all([parsed_url.scheme, parsed_url.netloc])
        except:
            is_url = False
        is_file = os.path.exists(data) and os.access(data, os.R_OK)
        is_data_url = data.startswith("data:")

        # If data is a file path, ensure it's readable
        if is_file:
            logger.info(f"Using file path: {data}")
        elif not (is_url or is_data_url):
            # If data is not a URL, file path, or data URL, assume it's plain text and encode it
            try:
                base64_encoded = base64.b64encode(data.encode('utf-8')).decode('utf-8')
                data = f"data:text/plain;base64,{base64_encoded}"
                logger.info(f"Encoded plain text input as base64 data URL: {data}")
            except Exception as e:
                logger.error(f"Error encoding plain text as base64: {str(e)}")
                return json.dumps({"error": f"Failed to encode plain text as base64: {str(e)}"})

        # If is_image is True and input is a file, validate it's a valid image
        if is_image and is_file:
            try:
                with Image.open(data) as img:
                    img.verify()  # Verify it's a valid image
                logger.info(f"Validated image file: {data}")
            except UnidentifiedImageError as e:
                logger.error(f"Invalid image file: {str(e)}")
                return json.dumps({"error": f"Input is not a valid image: {str(e)}"})

        # Always do a dry run first if not confirmed
        if not confirm:
            dry_run = True
            result = inscribe_ordinal(
                data=data,
                fee_rate=fee_rate,
                dry_run=True
            )
            fee_info = result.get("output", result.get("fee_estimate", ""))
            return json.dumps({
                "confirmation_required": True,
                "fee_estimate": fee_info,
                "message": "This inscription will cost the above fee. Call this tool again with confirm=True to proceed.",
                "dry_run_result": result
            }, indent=2)

        # If confirmed, actually inscribe (broadcast)
        result = inscribe_ordinal(
            data=data,
            fee_rate=fee_rate,
            dry_run=False
        )

        # If is_image is True and input was a URL or base64, validate the resulting file
        if is_image and (is_url or is_data_url) and result.get("success"):
            file_path = result.get("file_path")
            if file_path and os.path.exists(file_path):
                try:
                    with Image.open(file_path) as img:
                        img.verify()
                    logger.info(f"Validated downloaded/decoded image: {file_path}")
                except UnidentifiedImageError as e:
                    logger.error(f"Invalid image content: {str(e)}")
                    return json.dumps({"error": f"Input resolved to an invalid image: {str(e)}"})

        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in wallet_inscribe_ordinal: {str(e)}")
        return json.dumps({"error": f"Error inscribing ordinal: {str(e)}"})

@mcp.tool()
def save_image_to_uploads(ctx: Context, data: str, filename: str = None) -> str:
    """
    Save an image provided by the user (file path, URL, or base64 data URL) into the 'uploads' folder.
    Returns the full file path of the saved image.

    Parameters:
    - data: Path to the image file, a URL, or a base64 data URL.
    - filename: Optional filename for the saved image (default: uses timestamp).

    Returns:
    - The full file path of the saved image, or an error message.
    """
    import os
    import base64
    import requests
    from io import BytesIO
    from PIL import Image, UnidentifiedImageError
    import time

    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    # Generate filename if not provided
    if not filename:
        filename = f"image_{int(time.time())}.jpg"
    save_path = os.path.join(uploads_dir, filename)

    try:
        # If data is a local file path
        if os.path.exists(data) and os.access(data, os.R_OK):
            with Image.open(data) as img:
                img = img.convert("RGB")
                img.save(save_path, format="JPEG")
            return save_path

        # If data is a base64 data URL
        elif data.startswith("data:image"):
            header, b64data = data.split(",", 1)
            img_bytes = base64.b64decode(b64data)
            with Image.open(BytesIO(img_bytes)) as img:
                img = img.convert("RGB")
                img.save(save_path, format="JPEG")
            return save_path

        # If data is a URL
        elif data.startswith("http://") or data.startswith("https://"):
            headers = {
                "User-Agent": "Mozilla/5.0"
            }
            resp = requests.get(data, headers=headers, allow_redirects=True, timeout=10)
            if resp.status_code != 200:
                return f"Error: Could not fetch image from URL ({resp.status_code})"
            # Check content-type
            content_type = resp.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                # Try to extract image from HTML if possible (not guaranteed)
                return "Error: URL did not return an image file (Content-Type: {}).".format(content_type)
            try:
                with Image.open(BytesIO(resp.content)) as img:
                    img = img.convert("RGB")
                    img.save(save_path, format="JPEG")
                return save_path
            except UnidentifiedImageError:
                # Log first 200 bytes for debugging
                snippet = resp.content[:200]
                return f"Error: Could not identify image file. First 200 bytes: {snippet!r}"

        else:
            return "Error: Unsupported input format. Provide a file path, image URL, or base64 data URL."
    except Exception as e:
        return f"Error saving image: {str(e)}"

@mcp.tool()
def compress_image_to_1k(ctx: Context, file_path: str, output_path: str = None) -> str:
    """
    Compress and resize a local image file so the resulting JPEG is under 1KB.
    Saves the compressed image and returns the new file path or an error message.

    Parameters:
    - file_path: Path to the original image file.
    - output_path: Optional path for the compressed image (default: adds '_compressed.jpg' to the original filename).

    Returns:
    - The file path of the compressed image, or an error message.
    """
    import os
    from io import BytesIO
    from PIL import Image

    max_bytes = 1024

    if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
        return f"Error: File '{file_path}' does not exist or is not readable"

    if output_path is None:
        base, ext = os.path.splitext(file_path)
        output_path = f"{base}_compressed.jpg"

    try:
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            min_dim = 16
            max_dim = min(img.width, img.height)
            for dim in range(max_dim, min_dim - 1, -8):
                resized = img.resize((dim, dim), Image.LANCZOS)
                for quality in range(40, 10, -5):
                    buffer = BytesIO()
                    resized.save(buffer, format="JPEG", quality=quality, optimize=True)
                    size = buffer.tell()
                    if size <= max_bytes:
                        # Save to output_path
                        buffer.seek(0)
                        with open(output_path, "wb") as f:
                            f.write(buffer.read())
                        return output_path
            return "Error: Could not compress image below 1KB"
    except Exception as e:
        return f"Error compressing image: {str(e)}"

# If this module is run directly, start the server
if __name__ == "__main__":
    try:
        logger.info("Starting Bitcoin MCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running Bitcoin MCP server: {str(e)}")
        traceback.print_exc()

