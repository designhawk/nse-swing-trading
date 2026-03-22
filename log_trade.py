"""Simple trade logger — log your paper or real trades to trades.csv

Usage:
    python log_trade.py buy HCLTECH --price 1603 --qty 12 --stop 1490 --target 1829
    python log_trade.py sell HCLTECH --price 1650 --date 2026-03-20
    python log_trade.py list                    # show all open trades
    python log_trade.py summary                 # show P&L summary
"""
import csv
import os
import sys
import argparse
from datetime import datetime

TRADES_FILE = "trades.csv"

def init_trades_file():
    """Create trades.csv if it doesn't exist."""
    if not os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Entry_Date', 'Symbol', 'Entry_Price', 'Qty', 'Stop_Price', 'Target_Price',
                             'Exit_Date', 'Exit_Price', 'PnL_Rs', 'PnL_Pct', 'Status', 'Notes'])

def read_trades():
    """Read all trades from CSV."""
    if not os.path.exists(TRADES_FILE):
        init_trades_file()
        return []
    with open(TRADES_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)

def write_trades(trades):
    """Write all trades back to CSV."""
    with open(TRADES_FILE, 'w', newline='') as f:
        if trades:
            writer = csv.DictWriter(f, fieldnames=trades[0].keys())
            writer.writeheader()
            writer.writerows(trades)

def cmd_buy(symbol, price, qty, stop, target, notes):
    """Log a new buy trade."""
    trades = read_trades()
    # Remove example row if it exists
    trades = [t for t in trades if t.get('Symbol') != 'HCLTECH' or t.get('Status') != 'OPEN' or t.get('Notes', '').startswith('Example') == False]

    today = datetime.now().strftime('%Y-%m-%d')
    trade = {
        'Entry_Date': today,
        'Symbol': symbol.upper(),
        'Entry_Price': f"{price:.2f}",
        'Qty': str(qty),
        'Stop_Price': f"{stop:.2f}",
        'Target_Price': f"{target:.2f}" if target else "",
        'Exit_Date': '',
        'Exit_Price': '',
        'PnL_Rs': '',
        'PnL_Pct': '',
        'Status': 'OPEN',
        'Notes': notes or ''
    }
    trades.append(trade)
    write_trades(trades)
    print(f"[OK] Logged BUY: {symbol} @ Rs {price:.2f}, Stop: Rs {stop:.2f}")

def cmd_sell(symbol, price, date=None, notes=None):
    """Close an open trade."""
    trades = read_trades()
    exit_date = date or datetime.now().strftime('%Y-%m-%d')

    found = False
    for trade in trades:
        if trade['Symbol'].upper() == symbol.upper() and trade['Status'] == 'OPEN':
            entry = float(trade['Entry_Price'])
            qty = int(trade['Qty'])
            exit_p = price
            pnl_rs = (exit_p - entry) * qty
            pnl_pct = (exit_p - entry) / entry * 100

            trade['Exit_Date'] = exit_date
            trade['Exit_Price'] = f"{exit_p:.2f}"
            trade['PnL_Rs'] = f"{pnl_rs:.2f}"
            trade['PnL_Pct'] = f"{pnl_pct:.2f}"
            trade['Status'] = 'CLOSED'
            if notes:
                trade['Notes'] = trade.get('Notes', '') + ' | Exit: ' + notes

            print(f"[OK] Logged SELL: {symbol} @ Rs {exit_p:.2f}")
            print(f"     P&L: Rs {pnl_rs:.2f} ({pnl_pct:+.2f}%)")
            found = True
            break

    if not found:
        print(f"[WARN] No open position found for {symbol}")
        return

    write_trades(trades)

def cmd_list():
    """Show all open trades."""
    trades = read_trades()
    open_trades = [t for t in trades if t['Status'] == 'OPEN']

    if not open_trades:
        print("No open trades.")
        return

    print(f"\n{'='*100}")
    print(f"OPEN POSITIONS ({len(open_trades)})")
    print(f"{'='*100}")
    print(f"{'Symbol':<18} {'Entry':>10} {'Qty':>6} {'Stop':>10} {'Target':>10} {'Days Held':>10}")
    print(f"{'-'*100}")

    today = datetime.now()
    for t in open_trades:
        entry_date = datetime.strptime(t['Entry_Date'], '%Y-%m-%d')
        days_held = (today - entry_date).days
        print(f"{t['Symbol']:<18} {float(t['Entry_Price']):>10.2f} {int(t['Qty']):>6} "
              f"{float(t['Stop_Price']):>10.2f} {float(t['Target_Price'] or 0):>10.2f} {days_held:>10}")

    print(f"{'='*100}")
    print("\nTo check current stop prices, run:")
    symbols = ' '.join(t['Symbol'] for t in open_trades)
    print(f"  python signals.py --refresh --held {symbols}")

def cmd_summary():
    """Show P&L summary."""
    trades = read_trades()
    closed = [t for t in trades if t['Status'] == 'CLOSED']
    open_trades = [t for t in trades if t['Status'] == 'OPEN']

    print(f"\n{'='*60}")
    print("TRADING SUMMARY")
    print(f"{'='*60}")
    print(f"Total trades:    {len(closed) + len(open_trades)}")
    print(f"Closed trades:   {len(closed)}")
    print(f"Open trades:     {len(open_trades)}")

    if closed:
        wins = [t for t in closed if float(t['PnL_Pct']) > 0]
        losses = [t for t in closed if float(t['PnL_Pct']) <= 0]
        total_pnl = sum(float(t['PnL_Rs']) for t in closed)
        avg_pnl = total_pnl / len(closed)
        win_rate = len(wins) / len(closed) * 100

        print(f"\nWin rate:        {win_rate:.1f}% ({len(wins)} wins / {len(losses)} losses)")
        print(f"Total P&L:       Rs {total_pnl:,.2f}")
        print(f"Avg P&L/trade:   Rs {avg_pnl:,.2f}")

        if wins:
            avg_win = sum(float(t['PnL_Pct']) for t in wins) / len(wins)
            print(f"Avg winner:      +{avg_win:.2f}%")
        if losses:
            avg_loss = sum(float(t['PnL_Pct']) for t in losses) / len(losses)
            print(f"Avg loser:       {avg_loss:.2f}%")

    print(f"{'='*60}")

def main():
    parser = argparse.ArgumentParser(description='Trade logger for NSE swing trading')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # buy command
    buy_parser = subparsers.add_parser('buy', help='Log a new buy trade')
    buy_parser.add_argument('symbol', help='Stock symbol (e.g., HCLTECH)')
    buy_parser.add_argument('--price', type=float, required=True, help='Entry price')
    buy_parser.add_argument('--qty', type=int, default=1, help='Quantity (default: 1)')
    buy_parser.add_argument('--stop', type=float, required=True, help='Stop loss price')
    buy_parser.add_argument('--target', type=float, help='Target price (optional)')
    buy_parser.add_argument('--notes', help='Notes about the trade')

    # sell command
    sell_parser = subparsers.add_parser('sell', help='Close an open trade')
    sell_parser.add_argument('symbol', help='Stock symbol (e.g., HCLTECH)')
    sell_parser.add_argument('--price', type=float, required=True, help='Exit price')
    sell_parser.add_argument('--date', help='Exit date (YYYY-MM-DD, default: today)')
    sell_parser.add_argument('--notes', help='Notes about the exit')

    # list command
    subparsers.add_parser('list', help='Show open trades')

    # summary command
    subparsers.add_parser('summary', help='Show P&L summary')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'buy':
        cmd_buy(args.symbol, args.price, args.qty, args.stop, args.target, args.notes)
    elif args.command == 'sell':
        cmd_sell(args.symbol, args.price, args.date, args.notes)
    elif args.command == 'list':
        cmd_list()
    elif args.command == 'summary':
        cmd_summary()

if __name__ == '__main__':
    main()
