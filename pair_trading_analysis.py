"""
Pair Trading Analysis Script
Converted from Jupyter Notebook
"""

# Install dependencies (uncomment if needed)
# import os
# os.system('pip install PyYAML pandas numpy statsmodels tqdm')

import sys
from pathlib import Path
import src.pipeline.pair_trading_pipeline as ptp
import src.utils.config_manager as cm
import warnings
warnings.filterwarnings('ignore')

print("✅ System ready! (modules reloaded)")

# PARAMETERS (modify if needed)
# Prompt user for data file(s)
data_files_input = input("Enter path(s) to COTAHIST .TXT file(s), separated by commas: ")
COTAHIST_FILES = [f.strip() for f in data_files_input.split(',') if f.strip()]

# Analysis parameters
TOP_N_STOCKS = 100          # Top liquid stocks to select
MIN_VOLUME = 500000         # Minimum daily volume (R$)
P_VALUE_MAX = 0.05          # Maximum p-value for cointegration
HURST_MAX = 0.5             # Maximum Hurst exponent
MIN_CROSSINGS = 24          # Minimum mean crossings in 2 years

print("Parameters set ✅")
print(f"Using {len(COTAHIST_FILES)} COTAHIST files")

# Apply parameters
config = cm.ConfigManager()
config.set('data.cotahist_files', COTAHIST_FILES)
config.set('liquidity.selection.top_n_stocks', TOP_N_STOCKS)
config.set('liquidity.selection.min_daily_volume', MIN_VOLUME)
config.set('analysis.cointegration.significance_level', P_VALUE_MAX)
config.set('analysis.hurst.max_hurst_exponent', HURST_MAX)
config.set('analysis.cross_mean.min_crossings_2y', MIN_CROSSINGS)

print("Parameters applied ✅")
print(f"COTAHIST files: {[f.split('/')[-1] for f in COTAHIST_FILES]}")

# Initialize pipeline
import importlib
modules_to_reload = [k for k in sys.modules.keys() if k.startswith('src.')]
for module_name in modules_to_reload:
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
importlib.reload(ptp)
importlib.reload(cm)
pipeline = ptp.PairTradingPipeline()
print("Pipeline ready 🚀 (ALL modules reloaded)")
pipeline.clear_cache()
print("Cache cleared - will use new folder structure")
import logging
logging.getLogger().setLevel(logging.WARNING)

# Verify output paths
print("📁 Output directories:")
test_config = cm.ConfigManager()
print(f"   Liquidity: {test_config.get_output_path('test.csv', 'liquidity')}")
print(f"   Price matrix: {test_config.get_output_path('test.csv', 'price_matrix')}")
print(f"   Cointegration: {test_config.get_output_path('test.csv', 'cointegration')}")
print(f"   Final results: {test_config.get_output_path('test.csv', 'final_results')}")
print("✅ Organized folders will be used")

# Debug: Check method signature
import inspect
sig = inspect.signature(test_config.get_output_path)
print(f"Method signature: {sig}")
try:
    liquidity_path = test_config.get_output_path('test.csv', 'liquidity')
    print("✅ New signature works")
except TypeError:
    print("⚠️ Using fallback - updating paths manually")
    base_path = Path().absolute()
    liquidity_path = str(base_path / 'outputs/01_liquidity/test.csv')
    price_path = str(base_path / 'outputs/02_price_matrix/test.csv')
    coin_path = str(base_path / 'outputs/03_cointegration/test.csv')
    final_path = str(base_path / 'outputs/05_final_results/test.csv')
    print("📁 Output directories (manual):")
    print(f"   Liquidity: {liquidity_path}")
    print(f"   Price matrix: {price_path}")
    print(f"   Cointegration: {coin_path}")
    print(f"   Final results: {final_path}")
    print("✅ Organized folders configured")

# RUN COMPLETE ANALYSIS
print("🚀 Running analysis...")
results = pipeline.execute_full_pipeline()
stats = pipeline.get_statistics()
print(f"✅ Analysis complete! {stats['final_selected_pairs']} pairs found")

# Top liquid stocks
results = pipeline.get_results()
if results['liquidity_analysis'] is not None:
    print("🏆 TOP 10 MOST LIQUID STOCKS:")
    la = results['liquidity_analysis']
    cols = ['ticker', 'nome_resumido']
    if 'score_liquidez' in la.columns:
        cols.append('score_liquidez')
    print(la[cols].head(10))

# Cointegrated pairs
if results['cointegrated_pairs'] is not None and not results['cointegrated_pairs'].empty:
    cp = results['cointegrated_pairs']
    print(f"🔬 COINTEGRATED PAIRS: {len(cp)}")
    print(f"Best p-value: {cp['p_valor_coint'].min():.6f}")
    print(cp[['Ativo_A', 'Ativo_B', 'p_valor_coint']].head(5))

# Final selected pairs
if results['final_pairs'] is not None and not results['final_pairs'].empty:
    final_df = results['final_pairs']
    print(f"🎯 FINAL PAIRS: {len(final_df)}")
    cols = ['Ativo_A', 'Ativo_B', 'p_valor_coint']
    if 'hurst_exponent' in final_df.columns:
        cols.append('hurst_exponent')
    print(final_df[cols])
    best = final_df.iloc[0]
    print(f"💡 BEST PAIR: {best['Ativo_A']}-{best['Ativo_B']} (p-value: {best['p_valor_coint']:.6f})")
else:
    print("❌ No pairs found. Try adjusting parameters.")

# Summary statistics
stats = pipeline.get_statistics()
print("📊 SUMMARY:")
print(f"   Liquid stocks: {stats['top_liquid_stocks']}")
print(f"   Pairs tested: {stats['total_pair_combinations']:,}")
print(f"   Cointegrated: {stats['cointegrated_pairs']}")
print(f"   Final pairs: {stats['final_selected_pairs']}")
if stats['total_pair_combinations'] > 0:
    rate = stats['final_selected_pairs'] / stats['total_pair_combinations'] * 100
    print(f"   Success rate: {rate:.4f}%")

# Save current configuration
config.save()
print("Config saved ✅")

# Organize files into folders
def organize_all_files():
    """Move existing files to organized folders"""
    root = Path('.')
    directories = [
        'data',
        'outputs/01_liquidity',
        'outputs/02_price_matrix',
        'outputs/03_cointegration',
        'outputs/04_filtered_pairs',
        'outputs/05_final_results'
    ]
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    moved_count = 0
    cotahist_patterns = ['COTAHIST_A*.TXT', 'COTAHIST_A*.txt']
    for pattern in cotahist_patterns:
        for cotahist_file in root.glob(pattern):
            target_path = Path('data') / cotahist_file.name
            if not target_path.exists():
                import shutil
                shutil.move(str(cotahist_file), str(target_path))
                moved_count += 1
                print(f"   📦 {cotahist_file.name} → data/")
    csv_dirs = {
        'outputs/01_liquidity': ['*acoes_liquidas*', '*tickers*'],
        'outputs/02_price_matrix': ['matriz_precos*'],
        'outputs/03_cointegration': ['*cointegrados*'],
        'outputs/04_filtered_pairs': ['*filtrados*'],
        'outputs/05_final_results': ['*finais*', '*selecionados*']
    }
    for csv_file in root.glob('*.csv'):
        file_moved = False
        for target_dir, patterns in csv_dirs.items():
            for pattern in patterns:
                if csv_file.match(pattern):
                    target_path = Path(target_dir) / csv_file.name
                    if not target_path.exists():
                        import shutil
                        shutil.move(str(csv_file), str(target_path))
                        moved_count += 1
                        file_moved = True
                        break
            if file_moved:
                break
    for txt_file in root.glob('*tickers*.txt'):
        target_path = Path('outputs/01_liquidity') / txt_file.name
        if not target_path.exists():
            import shutil
            shutil.move(str(txt_file), str(target_path))
            moved_count += 1
    if moved_count > 0:
        print(f"📁 Organized {moved_count} files into folders")
    else:
        print("📁 All files already organized")
    print("\n📂 File organization:")
    data_files = list(Path('data').glob('*')) if Path('data').exists() else []
    print(f"   data/: {len(data_files)} files")
    if data_files:
        for f in sorted(data_files):
            print(f"      • {f.name}")
    for dir_path in sorted([d for d in directories if d.startswith('outputs')]):
        if Path(dir_path).exists():
            files = list(Path(dir_path).glob('*'))
            print(f"   {dir_path}: {len(files)} files")

organize_all_files()
