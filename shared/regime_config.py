class RegimeConfig:
    VIX_THRESHOLD = 16.5

    CONFIG_A = {
        "entry_time": "09:25",
        "sl_pct": 40,
        "profit_target_pct": 70,
        "otm": 100,
        "margin_per_lot": 110000,
        "label": "HIGH_VIX_MODE"
    }

    CONFIG_B = {
        "entry_time": "09:20",
        "sl_pct": 25,
        "profit_target_pct": 30,
        "otm": 150,
        "margin_per_lot": 97500,
        "label": "LOW_VIX_MODE"
    }

    @staticmethod
    def get_config(current_vix: float) -> dict:
        if current_vix >= RegimeConfig.VIX_THRESHOLD:
            return RegimeConfig.CONFIG_A
        return RegimeConfig.CONFIG_B

    @staticmethod
    def log_regime(current_vix: float):
        config = RegimeConfig.get_config(current_vix)
        print(f"[REGIME] VIX={current_vix:.2f} \u2192 {config['label']} | "
              f"Entry={config['entry_time']} | SL={config['sl_pct']}% | "
              f"PT={config['profit_target_pct']}% | OTM={config['otm']} | "
              f"Margin/Lot=Rs.{config['margin_per_lot']}")
        return config
