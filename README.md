# Bitcoin MCP

Bitcoin MCP is a Model Context Protocol (MCP) server that integrates with Bitcoin Core through `bitcoin-cli` to provide AI utilities, such as Claude Desktop, with real-time access to Bitcoin blockchain data and wallet functionality. This server enables both read-only blockchain queries and active wallet operations, including sending Bitcoin and inscribing ordinals, making it a powerful tool for interacting with the Bitcoin network.

## Features

- Query real-time Bitcoin blockchain data, including blocks and network info
- Perform wallet operations like checking balances, sending Bitcoin, and inscribing ordinals (including images)
- Estimate transaction fees before sending or inscribing
- Support for mainnet, testnet, and signet networks
- Secure and efficient integration with Bitcoin Core via `bitcoin-cli` and `ord` for ordinal inscriptions

## Prerequisites

- Python 3.10+
- Bitcoin Core full node with `bitcoin-cli` installed
- `ord` command-line tool for ordinal inscriptions
- Claude Desktop or another MCP-compatible client
- Operating system: Windows, Linux, or macOS
- Required Python packages (see `requirements.txt`)

## Installation

1. **Clone the repository** to your Bitcoin full-node machine:
   ```bash
   git clone https://github.com/your-username/bitcoin-mcp-hackathon-project
   cd bitcoin-mcp-hackathon-project
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Bitcoin Core**:
   - Ensure Bitcoin Core is running and fully synced.
   - Create or edit a `.env` file in the project root with the following:
     ```env
     BITCOIN_CLI_PATH=/path/to/bitcoin-cli
     ORD_PATH=/path/to/ord
     BITCOIN_NETWORK=mainnet  # or testnet, signet
     BITCOIN_DATADIR=/path/to/bitcoin/data  # optional
     BITCOIN_CONF=/path/to/bitcoin.conf     # optional
     ```
     Example for Windows:
     ```env
     BITCOIN_CLI_PATH=C:\\Program Files\\Bitcoin\\daemon\\bitcoin-cli.exe
     ORD_PATH=C:\\Program Files\\ord\\ord.exe
     BITCOIN_NETWORK=mainnet
     ```

4. **Configure Claude Desktop** (or other MCP clients):
   - Update the MCP server configuration in your client:
     ```json
     {
       "mcpServers": {
         "bitcoin-mcp": {
           "command": "python",
           "args": ["path/to/bitcoin-mcp/bitcoin_mcp_server.py"],
           "env": {}
         }
       }
     }
     ```
   - Replace `path/to/bitcoin-mcp` with the absolute path to your project directory.

5. **Test the server**:
   ```bash
   python bitcoin_mcp_server.py
   ```
   This will start the MCP server and verify connectivity to Bitcoin Core. Look for logs confirming a successful connection to Bitcoin Core, including network, block count, and version details.

## Available Tools

The Bitcoin MCP server exposes a focused set of tools for blockchain queries, wallet operations, and ordinal inscriptions, accessible through MCP clients like Claude Desktop.

### Blockchain Information

| Tool                   | Description                                         |
|------------------------|-----------------------------------------------------|
| `get_blockchain_info`  | Retrieve the current state of the blockchain        |
| `get_block_hash`       | Get the hash for a specific block height            |
| `get_block`            | Fetch block data by hash with customizable verbosity|
| `estimate_smart_fee`   | Estimate fee rates for transaction confirmation     |
| `get_network_info`     | Fetch network connection and settings details       |

### Wallet Operations

| Tool                     | Description                                      |
|--------------------------|--------------------------------------------------|
| `get_wallet_balance_tool`| Get the wallet's balance in satoshis             |
| `wallet_send_bitcoin`    | Send Bitcoin to a specified address (with fee confirmation prompt) |
| `wallet_get_transactions`| Retrieve the wallet's transaction history        |
| `wallet_inscribe_ordinal`| Inscribe data (text, images, etc.) as a Bitcoin ordinal (with fee confirmation prompt) |
| `save_image_to_uploads`  | Save an image to the uploads folder for inscription|
| `compress_image_to_1k`   | Compress an image to under 1KB for inscription   |

> **Note:**  
> For sending Bitcoin and inscribing ordinals, the server will always perform a dry run first and prompt you with the estimated fee. You must confirm the operation to actually broadcast the transaction or inscription.

## Code Structure

- `bitcoin_mcp_server.py`: Main entry point defining the MCP server and its tools
- `bitcoin_connection.py`: Utilities for establishing and managing connections to Bitcoin Core
- `bitcoin_wallet.py`: Functions for wallet interactions, including sending Bitcoin and inscribing ordinals
- `bitcoin_utils.py`: General-purpose blockchain data utilities

## Security Notes

- **Wallet Operations**: Tools like `wallet_send_bitcoin` and `wallet_inscribe_ordinal` interact with real funds. Always double-check addresses, amounts, and data before executing.
- **Read-Only Queries**: Blockchain information tools are read-only and safe for general use.
- **Localhost Binding**: The server binds to `localhost` (127.0.0.1) by default to prevent external access.
- **Network Configuration**: Ensure the `BITCOIN_NETWORK` setting matches your Bitcoin Core instance to avoid unintended mainnet transactions.
- **File Permissions**: Verify that the server process has access to Bitcoin Core's data directory and `ord` executable.

## Example Usage

Interact with the Bitcoin MCP server through an MCP client like Claude Desktop using these example commands:

**Check blockchain status**:
```
What's the current state of the Bitcoin blockchain?
```

**Inspect a block**:
```
Show me details about block 850000
```

**Estimate transaction fee**:
```
Estimate the fee to send a transaction with confirmation in 2 blocks.
```

**Check wallet balance**:
```
What's my Bitcoin wallet balance?
```

**Send Bitcoin**:
```
Send 50000 satoshis to bc1qexampleaddress with a fee rate of 1 sat/vB
```
*You will be prompted with a fee estimate before confirming the transaction.*

**Inscribe an ordinal**:
```
Inscribe "My first ordinal" as a Bitcoin ordinal with a fee rate of 10 sat/vB
```
*You will be prompted with a fee estimate before confirming the inscription.*

**Inscribe an image as an ordinal**:
```
Inscribe the image at https://example.com/image.png as a Bitcoin ordinal.
```

---
