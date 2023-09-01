import numpy as np
import liquidity
from decimal import Decimal


def backtest(row, mini, maxi, target, base):

    decimal0 = row['pool.token0.decimals']
    decimal1 = row['pool.token1.decimals']
    decimal = decimal1-decimal0

    # calculate my liquidity
    
    SMIN=np.sqrt(mini* 10 ** (decimal))
    SMAX=np.sqrt(maxi* 10 ** (decimal))
    
    if base == 0:
        sqrt0 = np.sqrt(row['close']* 10 ** (decimal))
        row['price0'] = row['close']
    
    else:
        sqrt0= np.sqrt(1/row['close']* 10 ** (decimal))
        row['price0']= 1/row['close']
        
    #if sqrt0<SMAX and sqrt0>SMIN:
    if row['type'] == 2:
            deltaL = target / ((sqrt0 - SMIN)  + (((1 / sqrt0) - (1 / SMAX)) * (row['price0']* 10 ** (decimal))))
            amount1 = deltaL * (sqrt0-SMIN)
            amount0 = deltaL * ((1/sqrt0)-(1/SMAX))* 10 ** (decimal)
            #print(f"2-{row['type']} : {amount1} - {amount0} \n")
    #elif sqrt0<SMIN or sqrt0>SMAX:
    elif row['type'] == 3:
            deltaL = target / (((1 / SMIN) - (1 / SMAX)) * (row['price0']))
            amount1 = 0
            amount0 = deltaL * (( 1/SMIN ) - ( 1/SMAX ))
            #print(f"3-{row['type']} : {amount1} - {amount0} \n")
    else:
            deltaL = target / (SMAX-SMIN) 
            amount1 = deltaL * (SMAX-SMIN)
            amount0 = 0
            #print(f"1-{row['type']} : {amount1} - {amount0} \n")
    
    myliquidity = liquidity.get_liquidity(row['price0'],mini,maxi,amount0,amount1,decimal0,decimal1, row['type'])
    
    #print("OK myliquidity",myliquidity)
    
    # Calculate ActiveLiq
    if base == 0:

        if row['high'] > mini and row['low'] < maxi and row['high'] != row['low']:
            row['ActiveLiq'] = (min(maxi,row['high']) - max(row['low'],mini)) / (row['high'] - row['low']) * 100
        else:
            row['ActiveLiq'] = 0

        amounts = liquidity.get_amounts(row['price0'], mini, maxi, myliquidity, decimal0, decimal1, row['type'])
        row['amount0'] = amounts[1]
        row['amount1'] = amounts[0]

        amountsunb = liquidity.get_amounts((row['price0']), 1.0001**(-887220), 1.0001**887220, 1, decimal0, decimal1, row['type'])
        row['amount0unb'] = amountsunb[1]
        row['amount1unb'] = amountsunb[0]

    else:

        if (1 / row['low']) > mini and (1 / row['high']) < maxi and row['high'] != row['low']:
            row['ActiveLiq'] = (min(maxi, 1 / row['low']) - max(1 / row['high'], mini)) / ((1 / row['low']) - (1 / row['high'])) * 100
        else:
            row['ActiveLiq'] = 0

        amounts = liquidity.get_amounts((row['price0']*10**(decimal)), mini, maxi, myliquidity, decimal0, decimal1, row['type'])
        row['amount0'] = amounts[0]
        row['amount1'] = amounts[1]

        amountsunb = liquidity.get_amounts((row['price0']), 1.0001**(-887220), 1.0001**887220, 1, decimal0, decimal1, row['type'])
        row['amount0unb'] = amountsunb[0]
        row['amount1unb'] = amountsunb[1]
    

    
    # Final fee calculation
    row['myliquidity'] = myliquidity
    row['myfee0'] = row['fee0token'] * myliquidity * row['ActiveLiq'] / 100
    row['myfee1'] = row['fee1token'] * myliquidity * row['ActiveLiq'] / 100


    #print(f"myfee0:{row['myfee0']} = fee0token:{row['fee0token']} * myliquidity:{myliquidity} * ActiveLiq:{row['ActiveLiq']} / 100 \n")
    #print(f"myfee1:{row['myfee1']} = fee1token:{row['fee1token']} * myliquidity:{myliquidity} * ActiveLiq:{row['ActiveLiq']} / 100 \n")

    return(row)
    

def calculate_report_round(dpd):

    # Calculate Total Closed Trades
    total_trades = len(dpd[dpd['ActiveLiq'] > 0])

    total_myfee = dpd['myfee0'].sum() + dpd['myfee0'].sum()


    result_dict = {
        "total_trades": total_trades,
        "total_myfee": total_myfee
    }
    return result_dict

def show_report_round( result_dict) :
    print(f"第{result_dict['Round']}次進場 \n")
    print(f"進場時間 : {result_dict['Start Date']} row:{result_dict['start_row']} \n")
    print(f"進場價格 : {result_dict['Etry Price']:.2f} \n")
    print(f"價格下限 : {result_dict['Stop Loss']:.2f} \n")
    print(f"價格上限 : {result_dict['Take Profit']:.2f} \n")
    print(f"投入ETH : {result_dict['Balance']:.2f} \n")

    print(f"出場時間 : {result_dict['End Date']} row:{result_dict['end_row']} \n")
    print(f"出場價格 : {result_dict['Exit Price']}.2f \n")
    print(f"持有期數  : {result_dict['Total Trades']} (小時) \n")

    print(f"Net Profit: {result_dict['Net Profit']:.6f}\n")          #資本利得+交易手續費
    print(f"Total Fee : {result_dict['Total Fee']:.6f} \n")         #交易手續費
    print(f"Market Profit : {result_dict['Market Profit']:.6f} \n") #資本利得
    print(f"==============================================\n")


'''
def calculate_report_metrics(lp_trades, annual_risk_free_rate=0.03):
    net_profit = 0
    total_closed_trades = 0
    percent_profitable = 0
    profit_factor = 0
    max_drawdown = 0
    avg_trade = 0
    avg_bars_in_trades = 0
    sharpe_ratio = 0
    sortino_ratio = 0

 
    # Calculate Net Profit
    net_profit = sum(lp_trades)

    # Calculate Total Closed Trades
    total_closed_trades = len(lp_trades)

    # Calculate Percent Profitable
    percent_profitable = sum(1 for t in lp_trades if t > 0) / total_closed_trades


     # Calculate Profit Factor
    positive_trades = [t for t in lp_trades if t > 0]
    negative_trades = [t for t in lp_trades if t < 0]

    profit_factor = sum(positive_trades) / abs(sum(negative_trades)) if negative_trades else np.nan

    # Calculate Max Drawdown
    max_drawdown = min(sum(lp_trades[:i]) - min(lp_trades[i:]) for i in range(len(lp_trades)))
    avg_trade = net_profit / total_closed_trades
    avg_bars_in_trades = len(lp_trades) / total_closed_trades

    std_dev = np.std(lp_trades)
    if len(negative_trades) >= 2:
        downside_dev = np.std(negative_trades)
    else:
        downside_dev = np.nan

    excess_return = avg_trade
    risk_free_return = annual_risk_free_rate / 252  # Assuming daily trading

    # 檢查std_dev是否為0
    if np.isclose(std_dev, 0.0):  # 使用np.isclose處理小數點精度問題
        sharpe_ratio = np.nan
    else:
        sharpe_ratio = (excess_return - risk_free_return) / std_dev


    if np.isclose(downside_dev, 0.0):  # 使用np.isclose處理小數點精度問題
        sortino_ratio = np.nan
    else:
        sortino_ratio = (excess_return - risk_free_return) / downside_dev
  
    result_dict = {
        "Type" : "LP",
        "Net Profit": net_profit,
        "Total Closed Trades": total_closed_trades,
        "Percent Profitable": percent_profitable,
        "Profit Factor": profit_factor,
        "Max Drawdown": max_drawdown,
        "Avg Trade": avg_trade,
        "Avg # Bars in Trades": avg_bars_in_trades,
        "Sharpe Ratio": sharpe_ratio,
        "Sortino Ratio": sortino_ratio
    }

    return result_dict
'''



'''
base = 0: 表示你以第一種資產（例如 ETH）作為基準。在這種情況下，你在計算中使用的價格是該資產對第二種資產（例如 USDC）的價格，並且你的數量也是以這種資產計算的。

base = 1: 表示你以第二種資產（例如 USDC）作為基準。在這種情況下，你在計算中使用的價格是該資產對第一種資產（例如 ETH）的價格，並且你的數量也是以這種資產計算的。

例如，假設你使用 base = 0，那麼你在計算價格時會使用 ETH 對 USDC 的價格，並且在計算數量時會使用 ETH 的數量。如果你使用 base = 1，則會相反。
'''