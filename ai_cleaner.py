#!/usr/bin/env python3
"""
AI Cleaner Module for Ultra Temp Cleaner Pro
-------------------------------------------
Provides intelligent file cleaning recommendations using machine learning
"""

import os
import time
import json
import logging
import hashlib
import threading
import pickle
import math
from typing import Dict, List, Any, Callable, Optional, Tuple, Set
from datetime import datetime, timedelta
from pathlib import Path
import random

# Try to import ML libraries
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Import local modules
from config import config_manager


class AIFileAnalyzer:
    """AI-powered file analyzer for smart cleaning recommendations"""
    
    def __init__(self):
        """Initialize AI file analyzer"""
        self.available = NUMPY_AVAILABLE and SKLEARN_AVAILABLE
        self.model = None
        self.model_trained = False
        self.training_data = []
        self.user_feedback = {}
        self.file_access_history = {}
        self.file_importance_scores = {}
        self.last_scan_results = None
        self.recommendation_history = []
        self.safety_patterns = []
        self.scanning = False
        self.progress_callback = None
        
        # Load safety patterns
        self._load_safety_patterns()
        
        # Load trained model if available
        self._load_model()
    
    def is_available(self) -> bool:
        """Check if AI cleaning is available
        
        Returns:
            True if AI cleaning is available, False otherwise
        """
        return self.available
    
    def _load_safety_patterns(self):
        """Load safety patterns to prevent deleting important files"""
        # Default safety patterns from config
        self.safety_patterns = config_manager.get("scanning", "protected_patterns", [])
        
        # Add additional safety patterns
        self.safety_patterns.extend([
            # System directories
            "windows", "system32", "program files", "programdata",
            "appdata\\local\\microsoft", "appdata\\roaming\\microsoft",
            
            # User directories
            "documents", "downloads", "pictures", "music", "videos",
            
            # Important file types
            ".docx", ".xlsx", ".pptx", ".pdf", ".txt",
            ".jpg", ".png", ".mp3", ".mp4", ".zip",
            
            # Development files
            "src", "source", "project", ".git", "node_modules",
            
            # Database files
            ".db", ".sqlite", ".mdb"
        ])
    
    def _load_model(self):
        """Load trained model if available"""
        if not self.available:
            return
        
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ai_model.pkl")
        
        try:
            if os.path.exists(model_path):
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
                self.model_trained = True
                logging.info("AI model loaded successfully")
            else:
                # Create a default model
                self._create_default_model()
                logging.info("Created default AI model")
        except Exception as e:
            logging.error(f"Error loading AI model: {e}")
            # Create a default model
            self._create_default_model()
    
    def _create_default_model(self):
        """Create a default model when no trained model is available"""
        if not self.available:
            return
        
        try:
            # Create a simple pipeline with a random forest classifier
            self.model = Pipeline([
                ('scaler', StandardScaler()),
                ('classifier', RandomForestClassifier(n_estimators=10, random_state=42))
            ])
            
            # Generate some synthetic training data
            X = np.random.rand(100, 5)  # 5 features
            y = np.random.randint(0, 2, 100)  # Binary classification (delete or keep)
            
            # Train the model on synthetic data
            self.model.fit(X, y)
            
            self.model_trained = True
        except Exception as e:
            logging.error(f"Error creating default model: {e}")
            self.model = None
            self.model_trained = False
    
    def _save_model(self):
        """Save trained model to disk"""
        if not self.available or not self.model:
            return
        
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        model_path = os.path.join(model_dir, "ai_model.pkl")
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(model_dir, exist_ok=True)
            
            # Save model
            with open(model_path, "wb") as f:
                pickle.dump(self.model, f)
            
            logging.info("AI model saved successfully")
        except Exception as e:
            logging.error(f"Error saving AI model: {e}")
    
    def _extract_features(self, file_info: Dict[str, Any]) -> List[float]:
        """Extract features from file information for model prediction
        
        Args:
            file_info: Dictionary with file information
            
        Returns:
            List of numerical features
        """
        try:
            # Basic features
            age_days = file_info.get('age_days', 0)
            size = file_info.get('size', 0)
            
            # Normalized size (log scale to handle wide range)
            norm_size = math.log1p(size) / 30.0  # log(1 + x) capped at ~30
            
            # Access history features
            path = file_info.get('path', '')
            last_access = self.file_access_history.get(path, {}).get('last_access', 0)
            access_count = self.file_access_history.get(path, {}).get('count', 0)
            
            # Time since last access in days
            days_since_access = (time.time() - last_access) / (60 * 60 * 24) if last_access > 0 else age_days
            
            # Frequency of access (normalized)
            access_frequency = min(1.0, access_count / 10.0) if age_days > 0 else 0
            
            # Extension type feature
            extension = os.path.splitext(path)[1].lower()
            
            # Map extensions to numerical values
            extension_groups = {
                'temp': ['.tmp', '.temp', '.bak', '.old', '.swp'],
                'cache': ['.cache', '.chk'],
                'logs': ['.log', '.dmp', '.crash'],
                'docs': ['.doc', '.docx', '.pdf', '.txt', '.rtf'],
                'media': ['.jpg', '.png', '.mp3', '.mp4', '.avi'],
                'archive': ['.zip', '.rar', '.7z', '.tar', '.gz'],
                'executable': ['.exe', '.dll', '.sys', '.com', '.bat']
            }
            
            ext_value = 0.5  # default value for unknown extensions
            
            for group_id, exts in enumerate(extension_groups.values()):
                if extension in exts:
                    ext_value = group_id / (len(extension_groups) - 1)
                    break
            
            # Safety score based on path and safety patterns
            safety_score = self._calculate_safety_score(file_info)
            
            # Importance score
            importance = self.file_importance_scores.get(path, 0.5)
            
            # Return feature vector
            return [
                norm_size,
                age_days / 365.0,  # Normalize age to years
                days_since_access / 365.0,  # Normalize to years
                access_frequency,
                ext_value,
                safety_score,
                importance
            ]
        
        except Exception as e:
            logging.error(f"Error extracting features: {e}")
            return [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]  # default values
    
    def _calculate_safety_score(self, file_info: Dict[str, Any]) -> float:
        """Calculate safety score for a file based on path and patterns
        
        Args:
            file_info: Dictionary with file information
            
        Returns:
            Safety score between 0.0 (safe to delete) and 1.0 (important, don't delete)
        """
        path = file_info.get('path', '').lower()
        
        # Check for safety patterns
        pattern_matches = sum(1 for pattern in self.safety_patterns if pattern.lower() in path)
        
        # Higher score means more important (shouldn't delete)
        safety_score = min(1.0, pattern_matches / 3.0)
        
        # Check for common temp/cache directories
        temp_indicators = ['temp', 'tmp', 'cache', 'caches', 'history']
        if any(indicator in path.lower() for indicator in temp_indicators):
            safety_score = max(0.0, safety_score - 0.3)  # Lower score for temp files
        
        # Adjust score for age - older files might be less important unless they're in important directories
        age_days = file_info.get('age_days', 0)
        if age_days > 90 and safety_score < 0.7:
            safety_score = max(0.0, safety_score - 0.2)  # Lower score for old files
        
        return safety_score
    
    def predict_deletion_candidates(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Predict which files should be deleted based on AI analysis
        
        Args:
            files: List of file information dictionaries
            
        Returns:
            Dictionary with prediction results
        """
        if not self.available or not self.model_trained:
            # Fallback to heuristic-based recommendations
            return self._heuristic_recommendations(files)
        
        try:
            # Extract features for each file
            features = [self._extract_features(file) for file in files]
            
            # Make predictions
            if len(features) > 0:
                X = np.array(features)
                try:
                    # Get probabilities for "should delete" class
                    probabilities = self.model.predict_proba(X)[:, 1]
                except:
                    # Fallback if predict_proba not available
                    predictions = self.model.predict(X)
                    probabilities = predictions.astype(float)
            else:
                probabilities = []
            
            # Create result with recommendations
            recommendations = {
                "safe_to_delete": [],
                "consider_deleting": [],
                "keep": []
            }
            
            total_size = 0
            safe_delete_size = 0
            consider_delete_size = 0
            
            for i, file_info in enumerate(files):
                if i < len(probabilities):
                    prob = probabilities[i]
                    
                    # Add prediction probability to file info
                    file_info['delete_probability'] = float(prob)
                    
                    # Calculate total size
                    size = file_info.get('size', 0)
                    total_size += size
                    
                    # Classify based on probability
                    if prob >= 0.7:
                        recommendations["safe_to_delete"].append(file_info)
                        safe_delete_size += size
                    elif prob >= 0.4:
                        recommendations["consider_deleting"].append(file_info)
                        consider_delete_size += size
                    else:
                        recommendations["keep"].append(file_info)
            
            # Sort recommendations by probability
            recommendations["safe_to_delete"].sort(key=lambda x: x.get('delete_probability', 0), reverse=True)
            recommendations["consider_deleting"].sort(key=lambda x: x.get('delete_probability', 0), reverse=True)
            recommendations["keep"].sort(key=lambda x: x.get('delete_probability', 0), reverse=True)
            
            # Save last scan results
            self.last_scan_results = {
                "timestamp": time.time(),
                "total_files": len(files),
                "total_size": total_size,
                "safe_delete_count": len(recommendations["safe_to_delete"]),
                "safe_delete_size": safe_delete_size,
                "consider_delete_count": len(recommendations["consider_deleting"]),
                "consider_delete_size": consider_delete_size,
                "keep_count": len(recommendations["keep"]),
                "formatted": {
                    "total_size": self._format_size(total_size),
                    "safe_delete_size": self._format_size(safe_delete_size),
                    "consider_delete_size": self._format_size(consider_delete_size)
                }
            }
            
            # Add to recommendation history
            self.recommendation_history.append({
                "timestamp": time.time(),
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "total_files": len(files),
                "safe_delete_count": len(recommendations["safe_to_delete"]),
                "safe_delete_size": safe_delete_size,
                "safe_delete_size_formatted": self._format_size(safe_delete_size)
            })
            
            # Limit history to 10 entries
            if len(self.recommendation_history) > 10:
                self.recommendation_history = self.recommendation_history[-10:]
            
            return {
                "success": True,
                "recommendations": recommendations,
                "summary": self.last_scan_results,
                "ai_available": True
            }
        
        except Exception as e:
            logging.error(f"Error predicting deletion candidates: {e}")
            # Fallback to heuristic-based recommendations
            return self._heuristic_recommendations(files)
    
    def _heuristic_recommendations(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate recommendations based on heuristics when AI model is not available
        
        Args:
            files: List of file information dictionaries
            
        Returns:
            Dictionary with recommendation results
        """
        recommendations = {
            "safe_to_delete": [],
            "consider_deleting": [],
            "keep": []
        }
        
        total_size = 0
        safe_delete_size = 0
        consider_delete_size = 0
        
        for file_info in files:
            score = 0.0
            path = file_info.get('path', '').lower()
            age_days = file_info.get('age_days', 0)
            size = file_info.get('size', 0)
            total_size += size
            
            # Common temp file patterns
            if (any(pattern in path for pattern in ['.tmp', '.temp', '.bak', '~', '.cache', '.crash']) or
                any(folder in path.split(os.sep) for folder in ['temp', 'tmp', 'cache', 'log', 'logs'])):
                score += 0.4
            
            # Age-based score
            if age_days > 90:
                score += 0.3
            elif age_days > 30:
                score += 0.2
            elif age_days > 7:
                score += 0.1
            
            # Reduce score for likely important files
            if self._is_likely_important(path):
                score -= 0.5
            
            # Assign to category based on score
            file_info['delete_probability'] = score
            
            if score >= 0.7:
                recommendations["safe_to_delete"].append(file_info)
                safe_delete_size += size
            elif score >= 0.3:
                recommendations["consider_deleting"].append(file_info)
                consider_delete_size += size
            else:
                recommendations["keep"].append(file_info)
        
        # Sort recommendations by score
        recommendations["safe_to_delete"].sort(key=lambda x: x.get('delete_probability', 0), reverse=True)
        recommendations["consider_deleting"].sort(key=lambda x: x.get('delete_probability', 0), reverse=True)
        recommendations["keep"].sort(key=lambda x: x.get('delete_probability', 0), reverse=True)
        
        # Save last scan results
        self.last_scan_results = {
            "timestamp": time.time(),
            "total_files": len(files),
            "total_size": total_size,
            "safe_delete_count": len(recommendations["safe_to_delete"]),
            "safe_delete_size": safe_delete_size,
            "consider_delete_count": len(recommendations["consider_deleting"]),
            "consider_delete_size": consider_delete_size,
            "keep_count": len(recommendations["keep"]),
            "formatted": {
                "total_size": self._format_size(total_size),
                "safe_delete_size": self._format_size(safe_delete_size),
                "consider_delete_size": self._format_size(consider_delete_size)
            }
        }
        
        # Add to recommendation history
        self.recommendation_history.append({
            "timestamp": time.time(),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total_files": len(files),
            "safe_delete_count": len(recommendations["safe_to_delete"]),
            "safe_delete_size": safe_delete_size,
            "safe_delete_size_formatted": self._format_size(safe_delete_size)
        })
        
        # Limit history to 10 entries
        if len(self.recommendation_history) > 10:
            self.recommendation_history = self.recommendation_history[-10:]
        
        return {
            "success": True,
            "recommendations": recommendations,
            "summary": self.last_scan_results,
            "ai_available": False
        }
    
    def _is_likely_important(self, path: str) -> bool:
        """Check if a file is likely important based on path and patterns
        
        Args:
            path: File path
            
        Returns:
            True if the file is likely important, False otherwise
        """
        path_lower = path.lower()
        
        # Check for safety patterns
        if any(pattern.lower() in path_lower for pattern in self.safety_patterns):
            return True
        
        # Check for important file extensions
        important_extensions = [
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf',
            '.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4', '.avi', '.mov',
            '.zip', '.rar', '.7z', '.tar', '.gz', '.sql', '.db', '.sqlite'
        ]
        
        if any(path_lower.endswith(ext) for ext in important_extensions):
            return True
        
        return False
    
    def record_file_access(self, file_path: str, access_type: str = "read"):
        """Record file access for learning
        
        Args:
            file_path: Path to accessed file
            access_type: Type of access (read, write, delete)
        """
        current_time = time.time()
        
        # Initialize if not exists
        if file_path not in self.file_access_history:
            self.file_access_history[file_path] = {
                "first_access": current_time,
                "last_access": current_time,
                "count": 0,
                "types": set()
            }
        
        # Update access history
        self.file_access_history[file_path]["last_access"] = current_time
        self.file_access_history[file_path]["count"] += 1
        self.file_access_history[file_path]["types"].add(access_type)
        
        # Update importance score
        self._update_importance_score(file_path, access_type)
    
    def _update_importance_score(self, file_path: str, access_type: str):
        """Update importance score based on access patterns
        
        Args:
            file_path: Path to file
            access_type: Type of access
        """
        # Initialize if not exists
        if file_path not in self.file_importance_scores:
            self.file_importance_scores[file_path] = 0.5  # default score
        
        current_score = self.file_importance_scores[file_path]
        
        # Update score based on access type
        if access_type == "read":
            # Reading files increases importance slightly
            current_score = min(1.0, current_score + 0.1)
        elif access_type == "write":
            # Writing to files increases importance more
            current_score = min(1.0, current_score + 0.2)
        elif access_type == "delete":
            # Deleting files sets importance to 0
            current_score = 0.0
        
        self.file_importance_scores[file_path] = current_score
    
    def provide_feedback(self, file_path: str, should_delete: bool):
        """Provide feedback for model training
        
        Args:
            file_path: Path to file
            should_delete: True if file should be deleted, False otherwise
        """
        # Add to feedback dictionary
        self.user_feedback[file_path] = {
            "timestamp": time.time(),
            "should_delete": should_delete
        }
        
        # Update training data if file info is available
        for results in [self.last_scan_results]:
            if results and "recommendations" in results:
                for category in ["safe_to_delete", "consider_deleting", "keep"]:
                    for file_info in results["recommendations"].get(category, []):
                        if file_info.get("path") == file_path:
                            # Extract features and add to training data
                            features = self._extract_features(file_info)
                            self.training_data.append((features, 1 if should_delete else 0))
                            break
        
        # Train model if we have enough new data
        if len(self.training_data) >= 10 and self.available:
            self._train_model()
    
    def _train_model(self):
        """Train model on collected data"""
        if not self.available:
            return
        
        try:
            # Convert training data to numpy arrays
            X = np.array([x for x, y in self.training_data])
            y = np.array([y for x, y in self.training_data])
            
            # Initialize model if needed
            if self.model is None:
                self.model = Pipeline([
                    ('scaler', StandardScaler()),
                    ('classifier', RandomForestClassifier(n_estimators=50, random_state=42))
                ])
                
                # Train model on all data
                self.model.fit(X, y)
            else:
                # Partial fit for online learning
                # RandomForestClassifier doesn't support partial_fit, so we retrain
                self.model.named_steps['classifier'].fit(
                    self.model.named_steps['scaler'].transform(X), y)
            
            self.model_trained = True
            
            # Save trained model
            self._save_model()
            
            logging.info("AI model trained successfully")
            
        except Exception as e:
            logging.error(f"Error training AI model: {e}")
    
    def analyze_user_behavior(self, files: List[Dict[str, Any]], callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Analyze user behavior to improve recommendations
        
        Args:
            files: List of file information dictionaries
            callback: Optional progress callback
            
        Returns:
            Dictionary with analysis results
        """
        if not self.available:
            return {"success": False, "error": "AI analysis not available"}
        
        self.scanning = True
        self.progress_callback = callback
        results = {
            "analyzed_files": 0,
            "access_patterns": {},
            "recommendations": {}
        }
        
        try:
            # Process files in batches for better UI responsiveness
            batch_size = 100
            total_files = len(files)
            
            for i in range(0, total_files, batch_size):
                if not self.scanning:
                    break
                
                batch = files[i:i+batch_size]
                
                # Process batch
                for file_info in batch:
                    path = file_info.get('path')
                    if not path:
                        continue
                    
                    # Check if file exists
                    if not os.path.exists(path):
                        continue
                    
                    try:
                        # Get file stats
                        stats = os.stat(path)
                        
                        # Record access times
                        atime = stats.st_atime
                        mtime = stats.st_mtime
                        ctime = stats.st_ctime
                        
                        # Check for recent access
                        now = time.time()
                        if atime > now - (7 * 24 * 60 * 60):  # accessed in last week
                            self.record_file_access(path, "read")
                        
                        if mtime > now - (7 * 24 * 60 * 60):  # modified in last week
                            self.record_file_access(path, "write")
                        
                        results["analyzed_files"] += 1
                    except:
                        pass
                
                # Report progress
                if callback:
                    progress = (i + len(batch)) / total_files
                    callback({
                        "progress": progress,
                        "analyzed_files": results["analyzed_files"],
                        "current_batch": i // batch_size + 1,
                        "total_batches": (total_files + batch_size - 1) // batch_size
                    })
            
            # Generate access pattern stats
            access_counts = {}
            for path, info in self.file_access_history.items():
                age = (time.time() - info["first_access"]) / (60 * 60 * 24)
                frequency = info["count"] / max(1, age)
                
                # Categorize by frequency
                frequency_category = "high" if frequency > 0.5 else "medium" if frequency > 0.1 else "low"
                
                if frequency_category not in access_counts:
                    access_counts[frequency_category] = 0
                access_counts[frequency_category] += 1
            
            results["access_patterns"] = access_counts
            
            # Generate learning-based recommendations
            if self.model_trained:
                # Get top recommendations
                recommendations = self.predict_deletion_candidates(files)
                results["recommendations"] = recommendations
            
            return {
                "success": True,
                "results": results
            }
        
        except Exception as e:
            logging.error(f"Error analyzing user behavior: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            self.scanning = False
    
    def get_recommendation_history(self) -> List[Dict[str, Any]]:
        """Get history of recommendations
        
        Returns:
            List of recommendation history entries
        """
        return self.recommendation_history
    
    def stop_analysis(self):
        """Stop ongoing analysis"""
        self.scanning = False
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in a human-readable format
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# Singleton instance
ai_cleaner = AIFileAnalyzer()

if __name__ == "__main__":
    # Test functionality
    logging.basicConfig(level=logging.INFO)
    
    print(f"AI Cleaner available: {ai_cleaner.is_available()}")
    
    # Generate some test files
    test_files = []
    for i in range(100):
        # Create a mix of file types
        if i % 4 == 0:
            path = f"C:/temp/test_{i}.tmp"
            age = random.randint(30, 200)
        elif i % 4 == 1:
            path = f"C:/Users/documents/important_{i}.docx"
            age = random.randint(1, 30)
        elif i % 4 == 2:
            path = f"C:/Windows/Logs/log_{i}.log"
            age = random.randint(5, 60)
        else:
            path = f"C:/Downloads/file_{i}.exe"
            age = random.randint(10, 100)
        
        test_files.append({
            "path": path,
            "size": random.randint(1000, 10000000),
            "age_days": age
        })
    
    # Get recommendations
    print("Generating recommendations...")
    results = ai_cleaner.predict_deletion_candidates(test_files)
    
    summary = results["summary"]
    print(f"Total files: {summary['total_files']}")
    print(f"Safe to delete: {summary['safe_delete_count']} files ({summary['formatted']['safe_delete_size']})")
    print(f"Consider deleting: {summary['consider_delete_count']} files ({summary['formatted']['consider_delete_size']})")
    print(f"Keep: {summary['keep_count']} files")
    
    # Print top recommendations
    print("\nTop 5 files safe to delete:")
    for i, file_info in enumerate(results["recommendations"]["safe_to_delete"][:5]):
        print(f"{i+1}. {file_info['path']} (confidence: {file_info.get('delete_probability', 0):.2f})") 