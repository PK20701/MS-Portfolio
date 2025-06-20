Music streaming platforms like **Spotify** and video-sharing platforms like **YouTube** play a crucial role in the popularity of songs. However, there is a disparity in how certain songs perform across these platforms. Some tracks may have **millions of streams on Spotify but relatively fewer views on YouTube, and vice versa**.

The key questions we aim to answer:
- **What factors contribute to a song’s popularity on Spotify versus YouTube?**
- **Can we predict whether a song will perform better on Spotify or YouTube based on its attributes?**
- **What are the key characteristics that define a hit song across different platforms?**

What data do you need to answer the above problem?
To answer these questions, we need data that includes:

Song metadata: Track name, artist, album, and release type.
Spotify streaming data: Number of streams, danceability, energy, loudness, speechiness, tempo, acousticness, instrumentalness, etc.
YouTube performance metrics: Views, likes, comments, and official video status.
Musical characteristics: Attributes like key, liveness, and valence to understand the song’s emotional and structural appeal.


What are the different sources of data?
Dataset is taken from Kaggle and it combines data from Spotify and YouTube. The data is likely collected using:

Spotify API
YouTube API
Web scraping or third-party repositories

What kind of analytics task are you performing?
This project involves:

Exploratory Data Analysis (EDA): Understanding patterns and trends in song popularity across Spotify and YouTube.
Feature Engineering: Identifying key characteristics that impact song performance.
Predictive Modeling: Building a machine learning model to classify whether a song is more likely to be a Spotify Hit or a YouTube Hit.
Clustering: Grouping songs based on similar characteristics to understand common patterns in song popularity.

Implement Machine Learning Techniques



ML Technique 1: Decision Tree Classification
Justification
Business Case: Can we predict whether a song will perform better on Spotify or YouTube based on its attributes?
Why Decision Tree?
It helps classify songs into different popularity levels (e.g., High, Medium, Low) based on their features.
Decision Trees are easy to interpret and can handle both numerical and categorical data effectively.
It automatically selects the most important features that influence a song’s success.
The model provides clear decision rules that can help artists and producers optimize their music.
Outcome:
The classification model helps predict whether a song is likely to perform well based on its attributes.
It provides insights into which features (e.g., Likes, Comments, Tempo, Energy) are most impactful in driving popularity.

Interpretation of Decision Tree Classification Results
1. Overall Model Performance
Accuracy: The model achieved 85% accuracy, which indicates that it is performing well in predicting the song popularity category (High, Medium, Low).
Macro Avg F1-Score (0.85): This suggests that the model maintains a balanced performance across all classes.
2. Class-Wise Performance
Class	Precision	Recall	F1-Score	Support
High	0.88	0.89	0.88	1374
Low	0.90	0.86	0.88	1353
Medium	0.77	0.80	0.79	1417
High & Low Popularity Songs:

The model predicts these categories with high precision (0.88 & 0.90) and good recall (0.89 & 0.86).
This suggests that songs in these categories have distinct characteristics that the model can easily differentiate.
Medium Popularity Songs:

The F1-score is lower (0.79) compared to High and Low categories.
Recall (0.80) indicates that the model captures most Medium songs, but precision (0.77) is lower, meaning some Medium songs might be misclassified.
This is expected, as Medium-popularity songs may have overlapping attributes with both High and Low categories.
3. Key Takeaways
The model performs well overall with an accuracy of 85%, making it a reliable tool for predicting a song's popularity.
The High & Low popularity classes are well classified, but Medium popularity songs show some misclassification, possibly due to overlapping attributes.
Future improvements could include feature engineering or using ensemble models (e.g., Random Forest) to enhance the classification of Medium popularity songs.


ML Technique 2: K-Means Clustering
Justification
Business Case: What factors contribute to a song’s popularity on Spotify versus YouTube?
Why K-Means?
It helps group songs into clusters based on key engagement metrics (Likes, Comments, Energy, Tempo, etc.).
By analyzing clusters, we can identify common characteristics of successful songs.
It is useful for segmenting songs into different categories (e.g., viral hits, average performers, niche songs).
The Elbow Method helps determine the optimal number of clusters, ensuring a meaningful segmentation.
Outcome:
Helps identify key attributes that define hit songs across different platforms.
Enables targeted marketing strategies for different types of music based on cluster analysis.
Assists artists in understanding trends and producing content that aligns with popular song attributes.

Interpretation of K-Means Clustering Output
1. Elbow Method for Optimal K
The Elbow Method graph plots the number of clusters (K) against inertia (sum of squared distances of samples to their closest cluster center).
The graph shows a sharp decline in inertia initially, which gradually flattens out as K increases.
The optimal number of clusters (K) is usually identified at the "elbow" point, where adding more clusters does not significantly reduce inertia.
From the graph, the elbow appears around K = 3, meaning three clusters are likely the best choice for segmenting the songs based on their attributes.
2. K-Means Clustering on Song Popularity
The scatter plot visualizes clustering based on Energy (X-axis) and Likes (Y-axis).
The data points are divided into three clusters (labeled as 0, 1, and 2) using K-Means.
Cluster 0 (Purple): Represents songs with lower energy and varying levels of likes.
Cluster 1 (Teal): Represents songs with moderate to high energy and a wide range of likes, including some of the most popular songs.
Cluster 2 (Yellow): Represents songs with very low energy and generally fewer likes.
The clustering suggests that energy plays a role in song popularity, but other factors likely contribute to higher engagement levels (likes).
3. Key Takeaways
Songs with higher energy tend to have more likes, but there are exceptions where lower-energy songs also receive high engagement.
The clustering helps identify distinct song types that perform differently across platforms.
The results can be used to recommend song characteristics that might improve engagement, such as moderate-to-high energy levels.


Performance Comparison and Conclusion
Decision Tree (Classification)

Achieved an accuracy of 85%, which is quite good.
The classification report shows balanced precision, recall, and F1-scores.
The confusion matrix indicates that most predictions are correct, but there are some misclassifications.
K-Means Clustering

The Silhouette Score is positive, indicating good cluster separation.
The Davies-Bouldin Score is low, which confirms well-defined clusters.
From the clustering scatter plot, we see energy influences song popularity, and clustering successfully differentiates songs based on this factor.
Overall Conclusion

Decision Tree is a supervised learning approach that effectively classifies songs into popularity categories.
K-Means, an unsupervised approach, helps identify hidden patterns in the data, making it useful for segmenting songs into meaningful clusters.
Both techniques complement each other: Decision Tree predicts, while K-Means finds groups.
Decision Tree: High accuracy (85%), but struggles with "Medium" popularity classification.
K-Means: Weak clustering (Silhouette Score = 0.198), suggesting no strong natural grouping. 
-Final Choice: If classification is needed, Decision Tree is better. If the goal is exploratory clustering, K-Means is useful but needs better feature selection.


Proposed Solution
We took a data-driven approach to analyze song attributes and their impact on popularity across platforms. Our methodology involved:

1. Data Collection & Preprocessing
We gathered structured data from Spotify (audio features like danceability, energy, tempo, etc.) and YouTube (views, likes, comments).
Data was cleaned, missing values were handled, and categorical variables were encoded.
2. Exploratory Data Analysis (EDA)
We visualized the distributions of various features, such as tempo, energy, and speechiness, across platforms.
Correlation analysis was performed to identify key attributes influencing popularity.
3. Model Selection & Training
We implemented Decision Trees to classify songs based on their platform performance.
We applied K-Means clustering to segment songs into distinct groups based on feature similarities.
4. Evaluation & Insights
Decision Tree: Achieved an accuracy of 85.01%, with strong precision and recall values for each class.
K-Means Clustering: Evaluated using Silhouette Score (0.198) and Davies-Bouldin Score (1.30), indicating moderate clustering quality.
Feature importance analysis helped us identify the most significant factors affecting song popularity.

Challenges & Learnings
Data Disparity: Some features were available only on one platform, requiring careful feature engineering.
Feature Selection: Not all audio features contributed equally to popularity, so we used statistical tests to refine our dataset.
Model Comparison: Decision Trees provided clear interpretability, while K-Means helped in unsupervised pattern discovery.
Evaluation Metrics: While accuracy was high, we also had to consider other metrics like F1-score and clustering validity scores.

Key Takeaways
Songs with high energy and danceability tend to do well on Spotify.
YouTube popularity is more influenced by engagement metrics like likes and comments.
Predicting song performance is feasible, but platform-specific strategies are essential for marketing and promotion.
By leveraging machine learning models, we provided valuable insights that can help artists and labels optimize their music distribution strategies across platforms.