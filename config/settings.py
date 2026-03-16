from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Wallet / Auth
    private_key: str = Field(default="", description="Polygon wallet private key (hex)")
    chain_id: int = Field(default=137, description="Polygon mainnet chain ID")

    # API Hosts
    polymarket_host: str = Field(default="https://polymarket.com")
    clob_host: str = Field(default="https://clob.polymarket.com")
    gamma_host: str = Field(default="https://gamma-api.polymarket.com")
    data_api_host: str = Field(default="https://data-api.polymarket.com")

    # Copy Trading Parameters
    poll_interval_seconds: int = Field(default=30)
    min_whale_pnl: float = Field(default=100_000.0, description="Minimum lifetime P&L in USD")
    min_win_rate: float = Field(default=0.65, description="Minimum win rate (0–1)")
    min_trades: int = Field(default=50, description="Minimum number of historical trades")
    max_tracked_wallets: int = Field(default=10)

    # Sizing
    bankroll: float = Field(default=100.0, description="Our starting bankroll in USD")
    min_trade_size: float = Field(default=1.0, description="Minimum order size in USD")
    max_trade_size: float = Field(default=20.0, description="Maximum order size in USD")

    # Risk Limits
    max_position_per_market: float = Field(default=20.0, description="Max USD per market")
    max_portfolio_exposure: float = Field(default=150.0, description="Max total exposure in USD")
    max_daily_loss: float = Field(default=10.0, description="Max daily loss before auto-shutdown")

    # Dashboard
    dashboard_port: int = Field(default=8050)
    dashboard_refresh_seconds: int = Field(default=10)

    # Mode
    dry_run: bool = Field(default=True, description="Paper trading mode — no real orders")

    # Notifications
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")


settings = Settings()
