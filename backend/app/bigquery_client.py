"""Google Cloud BigQuery client for database operations"""

import json
import uuid
from google.cloud import bigquery
from google.oauth2 import service_account
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class BigQueryClient:
    """Client for Google Cloud BigQuery operations"""
    
    def __init__(self):
        self.client: Optional[bigquery.Client] = None
        self.dataset_id = settings.bigquery_dataset_id
        self.project_id = settings.gcp_project_id
        self._initialized = False
        
    async def connect(self):
        """Initialize BigQuery client"""
        if self._initialized and self.client:
            return
            
        try:
            if not self.project_id:
                logger.warning("GCP_PROJECT_ID not set, BigQuery will not be available")
                return
                
            # Use service account credentials from environment
            credentials_path = settings.gcp_credentials_path
            if credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                self.client = bigquery.Client(
                    project=self.project_id,
                    credentials=credentials
                )
            else:
                # Use default credentials (for Cloud Run/Cloud Functions)
                self.client = bigquery.Client(project=self.project_id)
            
            # Ensure dataset exists
            await self._ensure_dataset_exists()
            
            # Ensure tables exist
            await self._ensure_tables_exist()
            
            self._initialized = True
            logger.info(f"✅ Connected to BigQuery: {self.project_id}.{self.dataset_id}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to BigQuery: {e}")
            self.client = None
    
    async def _ensure_dataset_exists(self):
        """Ensure the dataset exists, create if it doesn't"""
        try:
            if not self.project_id or not self.dataset_id:
                raise ValueError(
                    f"Missing required configuration: project_id={self.project_id}, dataset_id={self.dataset_id}. "
                    "Please check your .env file has GCP_PROJECT_ID and BIGQUERY_DATASET_ID set."
                )
            
            # Create dataset reference using DatasetReference
            dataset_ref = bigquery.DatasetReference(self.project_id, self.dataset_id)
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = settings.gcs_bucket_location if settings.gcs_bucket_location else "us-central1"
            dataset = self.client.create_dataset(dataset, exists_ok=True)
            logger.info(f"✅ Dataset {self.dataset_id} ready")
        except Exception as e:
            logger.error(f"Error ensuring dataset exists: {e}")
            raise
    
    async def _ensure_tables_exist(self):
        """Ensure all required tables exist"""
        # User profiles table
        user_profiles_schema = [
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("email", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("phone_number", "STRING"),
            bigquery.SchemaField("first_name", "STRING"),
            bigquery.SchemaField("last_name", "STRING"),
            bigquery.SchemaField("name", "STRING"),
            bigquery.SchemaField("adventurous", "FLOAT64"),
            bigquery.SchemaField("cultural", "FLOAT64"),
            bigquery.SchemaField("foodie", "FLOAT64"),
            bigquery.SchemaField("nature_lover", "FLOAT64"),
            bigquery.SchemaField("history_buff", "FLOAT64"),
            bigquery.SchemaField("social", "FLOAT64"),
            bigquery.SchemaField("preferences", "JSON"),
            bigquery.SchemaField("social_media_data", "JSON"),
            bigquery.SchemaField("travel_history", "JSON"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
            bigquery.SchemaField("updated_at", "TIMESTAMP"),
        ]
        
        # Interaction logs table
        interaction_logs_schema = [
            bigquery.SchemaField("interaction_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("interaction_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("content", "JSON"),
            bigquery.SchemaField("metadata", "JSON"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        ]
        
        # Recommendation scores table
        recommendation_scores_schema = [
            bigquery.SchemaField("recommendation_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("item_id", "STRING"),
            bigquery.SchemaField("item_name", "STRING"),
            bigquery.SchemaField("category", "STRING"),
            bigquery.SchemaField("match_score", "FLOAT64"),
            bigquery.SchemaField("personality_match_scores", "JSON"),
            bigquery.SchemaField("recommendation_data", "JSON"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
        ]
        
        # Chat logs table
        chat_logs_schema = [
            bigquery.SchemaField("chat_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("message", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("response", "STRING"),
            bigquery.SchemaField("message_type", "STRING"),
            bigquery.SchemaField("metadata", "JSON"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        ]
        
        tables_config = [
            ("user_profiles", user_profiles_schema),
            ("interaction_logs", interaction_logs_schema),
            ("recommendation_scores", recommendation_scores_schema),
            ("chat_logs", chat_logs_schema),
        ]
        
        for table_name, schema in tables_config:
            try:
                table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
                table = bigquery.Table(table_id, schema=schema)
                table = self.client.create_table(table, exists_ok=True)
                logger.info(f"✅ Table {table_name} ready")
            except Exception as e:
                logger.error(f"Error creating table {table_name}: {e}")
    
    def _is_available(self) -> bool:
        """Check if BigQuery is available"""
        return self.client is not None and self._initialized
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by user_id"""
        if not self._is_available():
            return None
            
        query = f"""
        SELECT *
        FROM `{self.project_id}.{self.dataset_id}.user_profiles`
        WHERE user_id = @user_id
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            for row in results:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    async def create_user_profile(self, profile_data: Dict[str, Any]) -> bool:
        """Create a new user profile"""
        if not self._is_available():
            return False
        
        # BigQuery requires email, but InstantDB doesn't store it
        # Use phone-based email as placeholder for BigQuery analytics
        email = profile_data.get("email")
        if not email and profile_data.get("phone_number"):
            email = f"{profile_data.get('phone_number')}@phone.local"
        elif not email:
            # Skip BigQuery if no email and no phone
            logger.warning("⚠️  Skipping BigQuery create: no email or phone_number")
            return False
            
        # Prepare data for BigQuery
        row_data = {
            "user_id": profile_data.get("user_id"),
            "email": email,
            "phone_number": profile_data.get("phone_number"),
            "first_name": profile_data.get("first_name"),
            "last_name": profile_data.get("last_name"),
            "name": profile_data.get("name"),
            "adventurous": profile_data.get("personality", {}).get("adventurous", 0.5) if isinstance(profile_data.get("personality"), dict) else getattr(profile_data.get("personality"), "adventurous", 0.5) if profile_data.get("personality") else 0.5,
            "cultural": profile_data.get("personality", {}).get("cultural", 0.5) if isinstance(profile_data.get("personality"), dict) else getattr(profile_data.get("personality"), "cultural", 0.5) if profile_data.get("personality") else 0.5,
            "foodie": profile_data.get("personality", {}).get("foodie", 0.5) if isinstance(profile_data.get("personality"), dict) else getattr(profile_data.get("personality"), "foodie", 0.5) if profile_data.get("personality") else 0.5,
            "nature_lover": profile_data.get("personality", {}).get("nature_lover", 0.5) if isinstance(profile_data.get("personality"), dict) else getattr(profile_data.get("personality"), "nature_lover", 0.5) if profile_data.get("personality") else 0.5,
            "history_buff": profile_data.get("personality", {}).get("history_buff", 0.5) if isinstance(profile_data.get("personality"), dict) else getattr(profile_data.get("personality"), "history_buff", 0.5) if profile_data.get("personality") else 0.5,
            "social": profile_data.get("personality", {}).get("social", 0.5) if isinstance(profile_data.get("personality"), dict) else getattr(profile_data.get("personality"), "social", 0.5) if profile_data.get("personality") else 0.5,
            "preferences": json.dumps(profile_data.get("preferences", {})) if profile_data.get("preferences") else None,
            "social_media_data": json.dumps(profile_data.get("social_media_data", {})) if profile_data.get("social_media_data") else None,
            "travel_history": json.dumps(profile_data.get("travel_history", [])) if profile_data.get("travel_history") else None,
            "created_at": (profile_data.get("created_at") or datetime.utcnow()).isoformat() if isinstance(profile_data.get("created_at"), (datetime, type(None))) else str(profile_data.get("created_at")),
            "updated_at": (profile_data.get("updated_at") or datetime.utcnow()).isoformat() if isinstance(profile_data.get("updated_at"), (datetime, type(None))) else str(profile_data.get("updated_at")),
        }
        
        table_id = f"{self.project_id}.{self.dataset_id}.user_profiles"
        errors = self.client.insert_rows_json(table_id, [row_data])
        
        if errors:
            logger.error(f"Error inserting user profile: {errors}")
            return False
        return True
    
    async def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user profile using MERGE to avoid streaming buffer issues
        
        MERGE is better at handling streaming buffer conflicts than UPDATE/DELETE
        """
        if not self._is_available():
            return False
        
        # Get existing profile to retrieve email (required by BigQuery schema)
        existing_profile = await self.get_user_profile(user_id)
        email = None
        if existing_profile:
            email = existing_profile.get("email")
        
        # If no existing profile and no email in update_data, use phone-based placeholder
        if not email:
            # Try to get phone from update_data or existing profile
            phone = update_data.get("phone_number") or (existing_profile.get("phone_number") if existing_profile else None)
            if phone:
                email = f"{phone}@phone.local"
            else:
                # Skip BigQuery update if we can't determine email
                logger.warning(f"⚠️  Skipping BigQuery update for {user_id}: no email available")
                return False
        
        # Prepare personality traits
        personality_fields = ["adventurous", "cultural", "foodie", "nature_lover", "history_buff", "social"]
        update_values = {}
        
        # Extract personality traits
        if "personality" in update_data and isinstance(update_data["personality"], dict):
            for trait in personality_fields:
                update_values[trait] = float(update_data["personality"].get(trait, 0.5))
        else:
            for trait in personality_fields:
                update_values[trait] = float(update_data.get(trait, 0.5))
        
        # Extract other update fields (exclude InstantDB-only fields)
        for key, value in update_data.items():
            if key not in ["personality", "characteristics_summary", "source_links"] + personality_fields:
                if key in ["preferences", "social_media_data", "travel_history"]:
                    update_values[key] = json.dumps(value) if value else (json.dumps([]) if key == "travel_history" else None)
                else:
                    update_values[key] = value
        
        # Ensure email is included for BigQuery (required field)
        update_values["email"] = email
        update_values["updated_at"] = datetime.utcnow().isoformat()
        
        # Build SET clause for MERGE
        set_clause_parts = []
        params = [bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
        
        for i, (key, value) in enumerate(update_values.items()):
            param_name = f"val_{i}"
            if isinstance(value, (int, float)):
                params.append(bigquery.ScalarQueryParameter(param_name, "FLOAT64", value))
            else:
                params.append(bigquery.ScalarQueryParameter(param_name, "STRING", value))
            set_clause_parts.append(f"t.{key} = @{param_name}")
        
        set_clause = ",\n    ".join(set_clause_parts)
        
        # Use MERGE instead of DELETE+UPDATE to handle streaming buffer better
        # Build INSERT column list and values (email must be included)
        insert_columns = ["user_id"] + list(update_values.keys())
        insert_values = ["@user_id"] + [f"@val_{i}" for i in range(len(update_values))]
        
        merge_query = f"""
        MERGE `{self.project_id}.{self.dataset_id}.user_profiles` t
        USING (SELECT @user_id as user_id) s
        ON t.user_id = s.user_id
        WHEN MATCHED THEN
          UPDATE SET
            {set_clause}
        WHEN NOT MATCHED THEN
          INSERT ({', '.join(insert_columns)})
          VALUES ({', '.join(insert_values)})
        """
        
        try:
            job_config = bigquery.QueryJobConfig(query_parameters=params)
            query_job = self.client.query(merge_query, job_config=job_config)
            query_job.result(timeout=30)  # 30 second timeout
            
            logger.info(f"✅ Successfully updated user profile {user_id} using MERGE")
            return True
            
        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"Error updating user profile with MERGE: {e}")
            if "streaming buffer" in error_str:
                logger.warning(f"⚠️  Still hitting streaming buffer after 30 seconds. This is a BigQuery limitation.")
                logger.info(f"💾 Personality was analyzed and is stored in cache for immediate use")
                logger.info(f"📌 BigQuery will accept updates after streaming buffer clears (~90+ minutes)")
                return False  # Return False but personality is in cache
            return False
    
    async def insert_interaction_log(self, log_data: Dict[str, Any]) -> bool:
        """Insert interaction log"""
        if not self._is_available():
            return False
            
        row_data = {
            "interaction_id": log_data.get("interaction_id", str(uuid.uuid4())),
            "user_id": log_data.get("user_id"),
            "interaction_type": log_data.get("interaction_type"),
            "content": json.dumps(log_data.get("content", {})) if log_data.get("content") else None,
            "metadata": json.dumps(log_data.get("metadata", {})) if log_data.get("metadata") else None,
            "timestamp": (log_data.get("timestamp") or datetime.utcnow()).isoformat() if isinstance(log_data.get("timestamp"), (datetime, type(None))) else str(log_data.get("timestamp", datetime.utcnow())),
        }
        
        table_id = f"{self.project_id}.{self.dataset_id}.interaction_logs"
        errors = self.client.insert_rows_json(table_id, [row_data])
        
        if errors:
            logger.error(f"Error inserting interaction log: {errors}")
            return False
        return True
    
    async def get_interaction_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get user interaction history"""
        if not self._is_available():
            return []
            
        query = f"""
        SELECT *
        FROM `{self.project_id}.{self.dataset_id}.interaction_logs`
        WHERE user_id = @user_id
        ORDER BY timestamp DESC
        LIMIT @limit
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            logs = []
            for row in results:
                log_dict = dict(row)
                # Parse JSON fields
                if log_dict.get("content") and isinstance(log_dict["content"], str):
                    log_dict["content"] = json.loads(log_dict["content"])
                if log_dict.get("metadata") and isinstance(log_dict["metadata"], str):
                    log_dict["metadata"] = json.loads(log_dict["metadata"])
                logs.append(log_dict)
            return logs
        except Exception as e:
            logger.error(f"Error getting interaction history: {e}")
            return []
    
    async def save_recommendation_score(
        self,
        user_id: str,
        item_id: str,
        item_name: str,
        category: str,
        match_score: float,
        personality_match_scores: Dict[str, float],
        recommendation_data: Dict[str, Any]
    ) -> bool:
        """Save recommendation score to BigQuery"""
        if not self._is_available():
            return False
            
        row_data = {
            "recommendation_id": str(uuid.uuid4()),
            "user_id": user_id,
            "item_id": item_id,
            "item_name": item_name,
            "category": category,
            "match_score": match_score,
            "personality_match_scores": json.dumps(personality_match_scores),
            "recommendation_data": json.dumps(recommendation_data),
            "created_at": datetime.utcnow().isoformat(),
        }
        
        table_id = f"{self.project_id}.{self.dataset_id}.recommendation_scores"
        errors = self.client.insert_rows_json(table_id, [row_data])
        
        if errors:
            logger.error(f"Error saving recommendation score: {errors}")
            return False
        return True
    
    async def save_chat_log(
        self,
        user_id: str,
        message: str,
        response: Optional[str] = None,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save chat log to BigQuery"""
        if not self._is_available():
            return False
            
        row_data = {
            "chat_id": str(uuid.uuid4()),
            "user_id": user_id,
            "message": message,
            "response": response,
            "message_type": message_type,
            "metadata": json.dumps(metadata or {}),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        table_id = f"{self.project_id}.{self.dataset_id}.chat_logs"
        errors = self.client.insert_rows_json(table_id, [row_data])
        
        if errors:
            logger.error(f"Error saving chat log: {errors}")
            return False
        return True


# Global instance
bigquery_client = BigQueryClient()
