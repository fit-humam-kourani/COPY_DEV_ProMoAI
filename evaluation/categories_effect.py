import pandas as pd
import os

def generate_final_leaderboard(
        categories_file,
        scores_file,
        output_file="final_leaderboard.csv"
):
    """
    Generates a final leaderboard table based on boolean-based clustering,
    including total average scores, sorted by the first cluster in descending order.

    Parameters:
    - categories_file: Path to the CSV file containing cluster assignments (TRUE/FALSE).
    - scores_file: Path to the CSV file containing model scores.
    - output_file: Path where the final leaderboard CSV will be saved.
    """

    # Read the categories CSV
    try:
        categories_df = pd.read_csv(categories_file, index_col=0)
    except Exception as e:
        print(f"Error reading categories file: {e}")
        return

    # Ensure there's at least one row
    if categories_df.empty:
        print("Categories file is empty.")
        return

    # Convert 'TRUE'/'FALSE' strings to boolean
    categories_df = categories_df.applymap(lambda x: str(x).strip().upper() == 'TRUE')

    # Read the model scores CSV
    try:
        scores_df = pd.read_csv(scores_file, index_col=0)
    except Exception as e:
        print(f"Error reading scores file: {e}")
        return

    # Find the intersection of processes in both categories and scores files
    processes_in_both = set(categories_df.columns) & set(scores_df.columns)

    if not processes_in_both:
        print("No overlapping process IDs found between categories and scores files.")
        return

    print(f"Processes considered (present in both files): {sorted(processes_in_both)}")

    # Filter categories_df and scores_df to only include these processes
    categories_df = categories_df[list(processes_in_both)]
    scores_df = scores_df[list(processes_in_both)]

    # Initialize a dictionary to store average scores per model per cluster
    leaderboard_data = {}

    # Calculate Total Average for each model
    leaderboard_data['Total Average'] = scores_df.mean(axis=1)

    # Iterate over each cluster and calculate average scores
    for cluster_name in categories_df.index:
        selected_processes = categories_df.loc[cluster_name]
        selected_processes = selected_processes[selected_processes].index.tolist()

        if not selected_processes:
            print(f"Cluster '{cluster_name}' has no processes marked as TRUE. Skipping.")
            continue

        print(f"\nCalculating average scores for cluster: '{cluster_name}' with processes: {selected_processes}")

        # Calculate the average score for each model based on the selected processes
        avg_scores = scores_df[selected_processes].mean(axis=1)

        # Store the average scores in the leaderboard data
        leaderboard_data[cluster_name] = avg_scores

    # Create a DataFrame from the leaderboard data
    leaderboard_df = pd.DataFrame(leaderboard_data)

    # Reset index to have 'Model' as a column instead of index
    leaderboard_df.reset_index(inplace=True)
    leaderboard_df.rename(columns={'index': 'Model'}, inplace=True)

    # Rearrange columns to have 'Total Average' as the first column, followed by cluster averages
    cluster_columns = [cluster for cluster in categories_df.index if cluster in leaderboard_df.columns]
    columns_order = ['Model', 'Total Average'] + cluster_columns
    leaderboard_df = leaderboard_df[columns_order]

    # Sort the DataFrame by the first cluster in descending order
    first_cluster = cluster_columns[0] if cluster_columns else None
    if first_cluster:
        leaderboard_df.sort_values(by=first_cluster, ascending=False, inplace=True)
    else:
        print("Warning: No cluster columns found to sort by.")

    # Save the final leaderboard to a CSV file
    try:
        leaderboard_df.to_csv(output_file, index=False)
        print(f"\nFinal leaderboard saved to: {output_file}")
    except Exception as e:
        print(f"Error saving final leaderboard: {e}")
        return

    print("\nFinal leaderboard generation completed successfully.")

# Example usage:
if __name__ == "__main__":
    # Define file paths
    categories_csv = r'C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\ground_truth\level_detail.csv'  # Replace with your actual categories file path
    scores_csv = r'C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\llm_com\f_measure.csv'  # Replace with your actual scores file path
    final_leaderboard_csv = r'C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\llm_com\leaderboard_detail.csv'  # Desired output file path

    # Generate the final leaderboard
    generate_final_leaderboard(categories_csv, scores_csv, final_leaderboard_csv)
