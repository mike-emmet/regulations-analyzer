import json
from collections import Counter
from openai import OpenAI
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from utils import clean_text


def analyze_comment_for_bot_likelihood(client, comment):
    """
    Use GPT-3.5-turbo to score comment's likelihood of being bot-generated
    Returns a score between 0 (human-like) and 5 (bot-like)
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You are an AI that can detect bot-generated comments. Score each comment from 0-5, \
                            where 0 means very likely human-written and 5 means extremely likely bot-generated."},
                {"role": "user",
                 "content": f"Analyze this comment and provide a score from 0-5 for bot likelihood:\n\n{comment}"}
            ]
        )

        # Extract the bot likelihood score
        bot_score_text = response.choices[0].message.content.strip()

        # Validate score is between 0-5
        try:
            bot_score = max(0, min(5, float(bot_score_text)))
        except ValueError:
            bot_score = 2.5  # Default middle score if parsing fails

        return bot_score

    except Exception as e:
        print(f"Error analyzing comment: {e}")
        return 2.5  # Default middle score


def analyze_comment_sentiment(client, comment):
    try:
        response = client.moderations.create(
            model="text-moderation-latest",
            input=comment
        )

        # Extract the categories

        response = response.results[0].categories

        return response

    except Exception as e:
        print(f"Error analyzing comment: {e}")
    return None  # Default middle score


def summarize_content(client, content):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You are an AI that can identify the theme and extract insights from the content."},
                {"role": "user",
                 "content": f"Analyze this content: \n\n{content}"}
            ]
        )

        summary = response.choices[0].message.content.strip()

        return summary

    except Exception as e:
        print(f"Error analyzing content: {e}")
        return ""


def read_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except json.JSONDecodeError:
        print(f"Error: File '{file_path}' contains invalid JSON.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None


def read_htm_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
            html_content = clean_text(html_content)
        return html_content
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None


def process_bot_comments(documents, client):
    """
    Read comments, score for bot likelihood, and update CSV
    """

    for document in documents:
        if document.get("Comments"):
            for comment in document.get("Comments"):
                if comment.get("Comment") and comment.get("Attachments", 0) == 0:
                    bot_score = analyze_comment_for_bot_likelihood(client, comment.get("Comment"))
                    sentiment = analyze_comment_sentiment(client, comment.get("Comment"))
                    comment['Bot_Likelihood_Score'] = bot_score
                    if sentiment:
                        comment['Sentiment'] = sentiment.__dict__
                    else:
                        comment['Sentiment'] = None
                    print(f"Processed Comment Bot Score = {bot_score}")

    return documents


def distribute_comments(comments, comments_with_attachments, all_comments):
    # Load the CSV data
    df = pd.DataFrame(comments)

    # Show basic info and statistics
    df_info = df.info()
    df_description = df.describe()
    print(df_info, df_description)

    # Analyze the distribution of scores
    score_distribution = df['Bot_Likelihood_Score'].value_counts().sort_index()

    # Generate word cloud for comment content
    comments_with_content = " ".join(df.get('Comment', "").dropna())
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(comments_with_content)

    # Plot the score distribution
    plt.figure(figsize=(8, 6))
    score_distribution.plot(kind='bar', color='skyblue', edgecolor='black')
    plt.title("Distribution of Bot Likelihood Scores")
    plt.xlabel("Bot_Likelihood_Score")
    plt.ylabel("Frequency")
    plt.xticks(rotation=0)
    plt.tight_layout()
    score_plot_path = 'images/score_distribution.png'
    plt.savefig(score_plot_path)

    # Plot the word cloud
    plt.figure(figsize=(10, 8))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title("Word Cloud of Comments")
    wordcloud_plot_path = 'images/comment_wordcloud.png'
    plt.savefig(wordcloud_plot_path)

    # Plot the ratio chart
    size1 = len(comments)
    size2 = len(comments_with_attachments)

    # Calculate ratio
    ratio = size1 / size2 if size2 != 0 else None

    # Data for the chart
    labels = ['Comments without attachments', 'Comments with attachments']
    sizes = [size1, size2]

    # Create a bar chart
    plt.figure(figsize=(8, 5))
    plt.bar(labels, sizes, color=['blue', 'orange'])

    # Add labels and title
    plt.title(f"Sizes and Ratio of Two Lists (Ratio: {ratio:.2f} if applicable)")
    plt.ylabel('Size')
    plt.xlabel('Lists')

    # Display the chart
    ratio_chart_path = 'images/comment_ratio.png'
    plt.savefig(ratio_chart_path)

    # Monthly Breakdown od comments
    # Extract months from Posted On attribute
    months = [pd.to_datetime(item['Posted On'], format='%b %d, %Y').strftime('%b') for item in all_comments]

    # Count occurrences of each month
    month_counts = Counter(months)

    # Sort month data in calendar order
    sorted_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_labels = [month for month in sorted_months if month in month_counts]
    month_values = [month_counts[month] for month in month_labels]

    # Create a bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(month_labels, month_values, color='skyblue')
    plt.title("Monthly Breakdown of Comments")
    plt.xlabel("Month")
    plt.ylabel("Number of Comments")
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    comments_monthly_breakdown_path = 'images/comments_monthly_breakdown.png'
    plt.savefig(comments_monthly_breakdown_path)

    # Create a chart for sentiment analysis
    sentiment_counts = {}
    for comment in comments:
        for sentiment, value in comment["Sentiment"].items():
            if value:  # Count only `True` values
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

    # Prepare data for the bar chart
    categories = list(sentiment_counts.keys())
    values = list(sentiment_counts.values())

    # Create the bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(categories, values, color='skyblue')
    plt.title('Sentiment Analysis Distribution', fontsize=16)
    plt.xlabel('Sentiment Categories', fontsize=12)
    plt.ylabel('Count', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Show the chart
    plt.tight_layout()
    comments_sentiment_analysis_path = 'images/comments_sentiment_analysis.png'
    plt.savefig(comments_sentiment_analysis_path)

    # Return key insights and plots
    df_info, df_description, score_distribution, score_plot_path, wordcloud_plot_path, ratio_chart_path, comments_monthly_breakdown_path, comments_sentiment_analysis_path


def summarize_docket(docket, client):

    summary = docket.get("Summary")
    agenda = docket.get("Agenda")
    content = f"SUMMARY:\n{summary}\n\nAGENDA:\n{agenda}"

    docket_theme = summarize_content(client, content)

    return docket_theme


def summarize_documents(documents, client):

    for document in documents:
        if document.get("Document"):
            document_raw = document.get("Document")
            summary = ""
            for key, value in document_raw.items():
                summary += f"{key}:\n{value}\n\n"
            document_summary = summarize_content(client, summary)
            document["Analysis"] = document_summary
        elif document.get("Document Path"):
            html_content = read_htm_file(document.get("Document Path", ""))
            document_summary = summarize_content(client, html_content)
            document["Analysis"] = document_summary
        else:
            document["Analysis"] = None

    return documents


def analyze(input_file, open_ai_key):
    docket = read_json_file(input_file)
    documents = docket.get("Documents", [])

    client = OpenAI(api_key=open_ai_key)

    # Run the processing
    new_documents = process_bot_comments(documents, client)
    new_documents = summarize_documents(new_documents, client)
    # Theme and insights of Docket
    docket_analysis = summarize_docket(docket, client)
    docket["Analysis"] = docket_analysis

    all_comments = []
    for document in documents:
        if document.get("Comments"):
            for comment in document.get("Comments"):
                all_comments.append(comment)

    comments_without_attachments = []
    comments_with_attachments = []
    for comment in all_comments:
        if comment.get("Attachments", 0) == 0:
            comments_without_attachments.append(comment)
        else:
            comments_with_attachments.append(comment)

    distribute_comments(comments_without_attachments, comments_with_attachments, all_comments)

    with open("docket_analysis.json", "w", encoding="utf-8") as json_file:
        docket["Documents"] = new_documents
        json.dump(docket, json_file, indent=4, ensure_ascii=False)

    print(f"\nAnalysis completed. Check results here:\n- {input_file}\n- docket_analysis.json\n- images/\n- downloads/")
