import pandas as pd
import os


def generate_final_leaderboard(
        activities_file,
        scores_file,
        output_file="final_leaderboard.csv"
):
    """
    Generates a final leaderboard table based on activity-based clustering,
    including total average scores, sorted by the first category (Up_to_12) in descending order.

    Parameters:
    - activities_file: Path to the CSV file containing number of activities per process.
    - scores_file: Path to the CSV file containing model scores.
    - output_file: Path where the final leaderboard CSV will be saved.
    """

    # Read the activities CSV
    try:
        activities_df = pd.read_csv(activities_file, index_col=0)
    except Exception as e:
        print(f"Error reading activities file: {e}")
        return

    # Ensure there's at least one row
    if activities_df.empty:
        print("Activities file is empty.")
        return

    # Extract the activities row
    # Assuming the first (and only) row contains the activity counts
    activities_series = activities_df.iloc[0]

    # Define clusters based on number of activities
    clusters = {
        'Up_to_13': (0, 13),
        'Higher': (14, float('inf'))
    }

    # Assign each process to a cluster
    process_to_cluster = {}
    for process, count in activities_series.items():
        try:
            count = float(count)
        except ValueError:
            print(f"Non-numeric activity count for process '{process}': {count}. Skipping.")
            continue
        for cluster_name, (lower, upper) in clusters.items():
            if lower <= count <= upper:
                process_to_cluster[process] = cluster_name
                break

    # Convert to DataFrame for easier manipulation
    cluster_df = pd.DataFrame.from_dict(process_to_cluster, orient='index', columns=['Cluster'])

    # Read the model scores CSV
    try:
        scores_df = pd.read_csv(scores_file, index_col=0)
    except Exception as e:
        print(f"Error reading scores file: {e}")
        return

    # Find the intersection of processes in both activities and scores files
    processes_in_both = set(cluster_df.index) & set(scores_df.columns)

    if not processes_in_both:
        print("No overlapping process IDs found between activities and scores files.")
        return

    print(f"Processes considered (present in both files): {sorted(processes_in_both)}")

    # Filter cluster_df and scores_df to only include these processes
    cluster_df = cluster_df.loc[list(processes_in_both)]
    scores_df = scores_df[list(processes_in_both)]

    # Initialize a dictionary to store average scores per model per cluster
    leaderboard_data = {}

    # Calculate Total Average for each model
    leaderboard_data['Total Average'] = scores_df.mean(axis=1)

    # Iterate over each cluster and calculate average scores
    for cluster_name in clusters.keys():
        selected_processes = cluster_df[cluster_df['Cluster'] == cluster_name].index.tolist()

        if not selected_processes:
            print(f"Cluster '{cluster_name}' has no processes. Skipping.")
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

    # Rearrange columns to have 'Total Average' as the first column
    columns_order = ['Model', 'Total Average'] + [cluster for cluster in clusters.keys()]
    # Ensure all columns are present
    columns_order = [col for col in columns_order if col in leaderboard_df.columns]
    leaderboard_df = leaderboard_df[columns_order]

    # Sort the DataFrame by the first category ('Up_to_12') in descending order
    first_category = list(clusters.keys())[0]
    if first_category in leaderboard_df.columns:
        leaderboard_df.sort_values(by=first_category, ascending=False, inplace=True)
    else:
        print(f"Warning: '{first_category}' column not found in leaderboard data.")

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
    activities_csv = r'C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\ground_truth\num_act.csv'
    scores_csv = r'C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\llm_com\f_measure.csv'
    process_ids_to_consider = [f"p{i}" for i in range(1, 21)]
    final_leaderboard_csv = r'C:\Users\kourani\git\ProMoAI\evaluation\llm_evaluation\llm_com\leaderboard_size7.csv'  # Desired output file path

    # Generate the final leaderboard
    generate_final_leaderboard(activities_csv, scores_csv, final_leaderboard_csv)
