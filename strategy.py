import csv

def calculate_bb_b(df, length, mult):
    
    basis = df['close'].rolling(window=length).mean()
    dev = mult * df['close'].rolling(window=length).std()
    upper = basis + dev
    lower = basis - dev
    df['bbr'] = (df['close'] - lower) / (upper - lower)
    return df
    
def generate_signals(df, ob, ob_close, os, os_close):
    df['signal'] = 0

    # Buy signal (long entry)
    buy_mask = (df['bbr'] < os) & (df['signal'].shift(1) == 0)
    df.loc[buy_mask, 'signal'] = 1

    # Sell signal (long exit)
    sell_mask = (df['bbr'] >= os_close) & (df['signal'].shift(1) == 1)
    df.loc[sell_mask, 'signal'] = -1

    # Sell signal (short entry)
    short_mask = (df['bbr'] > ob) & (df['signal'].shift(1) == 0)
    df.loc[short_mask, 'signal'] = -1

    # Buy signal (short exit)
    cover_mask = (df['bbr'] <= ob_close) & (df['signal'].shift(1) == -1)
    df.loc[cover_mask, 'signal'] = 1

    return df


def my_strategy(df):
    df = calculate_bb_b(df, length=21, mult=2.0)
    df = generate_signals(df, ob=1.2, ob_close=1.0, os=-0.2, os_close=0.2)
    return df

