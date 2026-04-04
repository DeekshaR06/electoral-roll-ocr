"""Analyze record types and find missing records."""
import pandas as pd

def analyze_types(excel_path):
    """Check record types distribution."""
    xl_file = pd.ExcelFile(excel_path)
    ws = xl_file.parse(sheet_name=0, header=None)
    
    header_row = None
    for idx, row in ws.iterrows():
        if isinstance(row[0], str) and 'Serial Number' in str(row[0]):
            header_row = idx
            break
    
    df = pd.read_excel(excel_path, sheet_name=0, header=header_row)
    
    print(f"Total records: {len(df)}")
    print(f"\nRecord Type Distribution:")
    types_count = df['Record Type'].value_counts()
    print(types_count)
    print()
    
    # Check for any null/NaN values
    print("Records with NaN Record Type:", df['Record Type'].isna().sum())
    print("Records with NaN Name:", df['Name'].isna().sum())
    print("Records with NaN EPIC:", df['EPIC Number'].isna().sum())
    
    # Show record types and their counts
    print("\nDetailed breakdown:")
    for rt in df['Record Type'].unique():
        if pd.notna(rt):
            count = len(df[df['Record Type'] == rt])
            print(f"  {rt}: {count}")

if __name__ == '__main__':
    analyze_types("output/voter_output.xlsx")
