# Tuya Smart Plug Power Monitor

AWS serverless application that monitors a Tuya/Smart Life smart plug and sends Telegram notifications when power is restored or lost.

## Features

- 🔌 **Real-time monitoring**: Polls Tuya Cloud API every minute
- 🛡️ **Debouncing**: Prevents false alerts from transient glitches (configurable, default 2 consecutive readings)
- 📱 **Telegram notifications**: Instant alerts with timestamps when power state changes
- 💾 **Persistent state**: Uses DynamoDB to maintain state across Lambda invocations
- 💰 **Cost-efficient**: Serverless architecture with pay-per-use pricing (no VPC, no NAT gateway)
- 🌍 **Timezone support**: Configurable timezone for message timestamps

## Architecture

- **AWS Lambda**: Python 3.11 function triggered every minute
- **EventBridge**: Scheduled rule for polling
- **DynamoDB**: State persistence (pay-per-request billing)
- **Tuya Cloud API**: Device status queries
- **Telegram Bot API**: Push notifications

## Prerequisites

1. **AWS Account** with AWS CLI configured

2. **AWS SAM CLI** installed:
   ```bash
   # macOS
   brew install aws-sam-cli
   
   # Linux (download from GitHub releases)
   curl -L https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip -o sam-cli.zip
   unzip sam-cli.zip -d sam-installation
   sudo ./sam-installation/install
   rm -rf sam-cli.zip sam-installation
   
   # Verify
   sam --version
   ```

3. **Python 3.11** and **uv** (Python package manager):
   ```bash
   # Install uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

4. **Tuya Cloud Account** and credentials (see below)

5. **Telegram Bot** token and chat ID (see below)

## Getting Tuya Credentials

1. **Create Tuya Cloud Project**:
   - Go to [Tuya IoT Platform](https://iot.tuya.com/)
   - Create account and log in
   - Go to **Cloud** → **Development**
   - Create new project (choose **Smart Home** as Development Method)

2. **Link Smart Life App**:
   - In your project, go to **Devices** → **Link Tuya App Account**
   - Scan QR code with Smart Life mobile app
   - Your devices will appear in the project

3. **Get API Credentials**:
   - In project overview, note:
     - **Access ID** (Client ID)
     - **Access Key** (Client Secret)
   - Note your **Endpoint** based on region:
     - Europe: `https://openapi.tuyaeu.com`
     - US: `https://openapi.tuyaus.com`
     - China: `https://openapi.tuyacn.com`
     - India: `https://openapi.tuyain.com`

4. **Get Device ID**:
   - In **Devices** tab, click your smart plug
   - Copy the **Device ID** (format: `bf...` or similar)

5. **Enable API Access**:
   - Go to **API** tab
   - Subscribe to **IoT Core** service (free tier available)
   - Authorize the following APIs:
     - `Device Management` → `Query Device Details`

## Getting Telegram Credentials

1. **Create Bot**:
   - Open Telegram, search for `@BotFather`
   - Send `/newbot` command
   - Follow prompts to name your bot
   - Save the **bot token** (format: `123456:ABC-DEF...`)

2. **Get Chat ID**:
   - **First**, send any message to your new bot (e.g., "hello")
   - Open browser and visit:
     ```
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
     ```
   - Find `"chat":{"id":123456789}` in the response
   - Save the **chat ID** (numeric)

   Alternatively, use `@userinfobot` to get your user ID.

## Quick Start

### 1. Set Up Environment

```bash
# Create virtual environment
invoke venv

# Activate it
source .venv/bin/activate

# Install dependencies
invoke install
```

### 2. Configure Credentials

```bash
cp config.template.yaml config.yaml
```

Edit `config.yaml` with your credentials:

```yaml
tuya:
  endpoint: "https://openapi.tuyaeu.com"
  access_id: "your_tuya_access_id"
  access_key: "your_tuya_access_key"
  device_id: "your_device_id"

telegram:
  bot_token: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
  chat_id: "123456789"

settings:
  debounce_count: 2
  timezone: "Europe/Kyiv"

aws:
  region: "eu-central-1"
  stack_name: "tuya-power-monitor"
  table_name: "power_watch_state"
  access_key_id: "AKIA..."
  secret_access_key: "your_secret"
```

> ⚠️ **Never commit `config.yaml`** - it contains secrets and is in `.gitignore`

### 3. Configure AWS CLI

```bash
invoke aws-configure
```

## Local Testing

**Always test locally before deploying!**

### Test All Integrations

```bash
invoke test-all
```

### Test Individual Components

```bash
# Test Tuya API connection
invoke test-tuya

# Test Telegram notification
invoke test-telegram

# Run a single poll (without DynamoDB)
invoke poll
```

### Run Unit Tests

```bash
invoke test
```

## Deployment

### 1. Generate SAM Configuration

```bash
invoke init
```

This creates:
- `samconfig.toml` - SAM deployment configuration with all parameters
- `env.json` - Environment variables for local testing

### 2. Verify Configuration

```bash
invoke show-config
```

### 3. Build and Deploy

```bash
invoke deploy
```

That's it! No prompts - all parameters come from your `config.yaml`.

## Available Commands

Run `invoke --list` to see all available commands:

| Command | Description |
|---------|-------------|
| **Setup** | |
| `invoke venv` | Create Python virtual environment |
| `invoke install` | Install development dependencies |
| `invoke aws-configure` | Configure AWS CLI from config.yaml |
| **Local Testing** | |
| `invoke test-tuya` | Test Tuya API connection |
| `invoke test-telegram` | Test Telegram notification |
| `invoke test-all` | Test all integrations (Tuya + Telegram) |
| `invoke poll` | Run a single poll locally (no DynamoDB) |
| `invoke test` | Run unit tests |
| `invoke test-cov` | Run unit tests with coverage |
| **Build & Deploy** | |
| `invoke init` | Generate SAM configuration from config.yaml |
| `invoke show-config` | Show deployment configuration |
| `invoke validate` | Validate SAM template |
| `invoke build` | Build SAM application |
| `invoke deploy` | Build and deploy to AWS |
| `invoke deploy-guided` | Build and deploy with guided prompts |
| **AWS Operations** | |
| `invoke logs` | View Lambda function logs |
| `invoke check-state` | Check current state in DynamoDB |
| `invoke invoke-remote` | Invoke Lambda function remotely |
| `invoke invoke-local` | Invoke Lambda function locally (requires Docker) |
| **Cleanup** | |
| `invoke clean` | Remove build artifacts |
| `invoke clean-all` | Remove all generated files |
| `invoke delete` | Delete all AWS resources |
| **Code Quality** | |
| `invoke lint` | Run linter (ruff) |
| `invoke lint-fix` | Run linter and fix issues |
| `invoke format` | Format code |
| `invoke typecheck` | Run type checker (mypy) |
| `invoke check` | Run all checks (lint + typecheck + test) |

## How It Works

### State Machine

The application maintains a debounced state machine:

1. **Initial State**: Unknown (`last_confirmed_online = null`)
2. **Observation**: Each poll reads device online status
3. **Debouncing**: 
   - If status matches previous observation → increment streak
   - If status differs → reset streak to 1
4. **Confirmation**: When streak ≥ `debounce_count`:
   - If initial state → establish baseline (no notification)
   - If state changed → send notification and update confirmed state
5. **Persistence**: State saved to DynamoDB after each run

### Example Flow

```
Poll 1: Device=online, State=unknown, Streak=1 → No action
Poll 2: Device=online, State=unknown, Streak=2 → Establish baseline (online)
Poll 3: Device=online, State=online, Streak=2 → No change
...
Poll 50: Device=offline, State=online, Streak=1 → Observed change, waiting
Poll 51: Device=offline, State=online, Streak=2 → Confirmed! Send "❌ Power OFF"
Poll 52: Device=offline, State=offline, Streak=2 → No change
...
Poll 75: Device=online, State=offline, Streak=1 → Observed change, waiting
Poll 76: Device=online, State=offline, Streak=2 → Confirmed! Send "✅ Power ON"
```

### Notification Format

```
✅ Power ON
2026-01-12 14:35:22 EET
```

```
❌ Power OFF
2026-01-12 18:42:15 EET
```

## Troubleshooting

### No notifications received

1. **Check Lambda logs**:
   ```bash
   invoke logs
   ```

2. **Verify Telegram bot**:
   - Send `/start` to your bot
   - Test locally:
     ```bash
     invoke test-telegram
     ```

3. **Check DynamoDB state**:
   ```bash
   invoke check-state
   ```

### Tuya API errors

**Error: "sign invalid"**
- Check Access ID and Access Key are correct in `config.yaml`
- Ensure API permissions are enabled in Tuya console

**Error: "device not found"**
- Verify Device ID is correct (case-sensitive)
- Ensure device is linked to your Tuya Cloud project

**Wrong endpoint**:
- EU users: `https://openapi.tuyaeu.com`
- US users: `https://openapi.tuyaus.com`
- Check your Tuya project's data center

Test your Tuya configuration:
```bash
invoke test-tuya
```

### Wrong timezone

Update `config.yaml` and redeploy:

```bash
# Edit config.yaml, then:
invoke init
invoke deploy
```

Valid timezones: `Europe/Kyiv`, `America/New_York`, `Asia/Tokyo`, etc.

### Lambda timeout

If Tuya API is slow, increase timeout in `template.yaml`:
```yaml
Globals:
  Function:
    Timeout: 30  # Increase from 20
```

Then redeploy:
```bash
invoke deploy
```

### False positives

If you get spurious notifications, increase `debounce_count` in `config.yaml`:

```yaml
settings:
  debounce_count: 3  # Increase from 2
```

Then regenerate and redeploy:
```bash
invoke init
invoke deploy
```

## Cost Estimate

Monthly costs (assuming 1-minute polling):

- **Lambda**: ~44,000 invocations/month
  - Free tier: 1M requests/month → **$0**
- **DynamoDB**: ~88,000 read/write operations
  - Free tier: 25 WCU/RCU → **$0**
- **EventBridge**: 44,000 events/month
  - Free tier: 1M events/month → **$0**

**Total: $0/month** (within free tier)

After free tier expires:
- Lambda: ~$0.01/month
- DynamoDB: ~$0.25/month
- EventBridge: $0.00
- **Total: ~$0.26/month**

## Cleanup

Delete all AWS resources:

```bash
invoke delete
```

Or via AWS CLI:
```bash
aws cloudformation delete-stack --stack-name tuya-power-monitor
```

This removes Lambda, DynamoDB table, EventBridge rule, and all associated resources.

## Project Structure

```
.
├── template.yaml           # SAM/CloudFormation template
├── config.template.yaml    # Configuration template (copy to config.yaml)
├── config.yaml             # Your configuration (gitignored)
├── samconfig.toml          # SAM config (generated, gitignored)
├── env.json                # Local env vars (generated, gitignored)
├── tasks.py                # Invoke tasks (replaces Makefile)
├── README.md               # This file
├── scripts/
│   ├── deploy.py           # Deployment helper (generates samconfig.toml)
│   └── test_local.py       # Local testing script
├── src/
│   ├── app.py              # Lambda handler
│   ├── requirements.txt    # Python dependencies
│   ├── config_loader.py    # Configuration loader
│   ├── tuya_client.py      # Tuya API wrapper
│   ├── state_store.py      # DynamoDB operations
│   ├── notifier.py         # Telegram sender
│   └── logic.py            # Core debounce logic
└── tests/
    └── test_logic.py       # Unit tests
```

## Security Notes

- Credentials are stored in `config.yaml` (gitignored) and passed as CloudFormation parameters
- `config.yaml`, `samconfig.toml`, and `env.json` are all in `.gitignore`
- For production, consider AWS Secrets Manager (adds cost)
- Lambda has minimal IAM permissions (DynamoDB + CloudWatch Logs only)
- No inbound network access (Lambda not in VPC)

## License

MIT

## Support

For issues with:
- **Tuya API**: Check [Tuya Developer Docs](https://developer.tuya.com/)
- **AWS SAM**: See [SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- **This project**: Open an issue or review logs with `invoke logs`
