# prompt_templates.py
"""
Module for managing prompt templates for the prompt engineering backend.
This keeps sensitive prompt templates secure on the server-side.
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class PromptTemplateManager:
    """
    Manager for loading and retrieving prompt templates
    """
    
    def __init__(self, templates_dir=None):
        """
        Initialize the prompt template manager
        
        Args:
            templates_dir (str, optional): Directory containing template files
        """
        if templates_dir is None:
            # Default to 'templates' directory in the same folder as this file
            self.templates_dir = Path(__file__).parent / 'templates'
        else:
            self.templates_dir = Path(templates_dir)
            
        # Create templates directory if it doesn't exist
        self.templates_dir.mkdir(exist_ok=True)
        
        # Templates cache
        self.templates = {}
        
        # Load all templates
        self._load_templates()
    
    def _load_templates(self):
        """Load all template files from the templates directory"""
        try:
            for template_file in self.templates_dir.glob('*.json'):
                try:
                    with open(template_file, 'r') as f:
                        template_data = json.load(f)
                        template_name = template_file.stem
                        self.templates[template_name] = template_data
                    logger.info(f"Loaded template: {template_name}")
                except Exception as e:
                    logger.error(f"Error loading template {template_file}: {str(e)}")
        except Exception as e:
            logger.error(f"Error scanning templates directory: {str(e)}")
    
    def get_template(self, template_name):
        """
        Get a template by name
        
        Args:
            template_name (str): Name of the template to retrieve
            
        Returns:
            dict: Template data or None if not found
        """
        if template_name in self.templates:
            return self.templates[template_name]
        else:
            logger.warning(f"Template not found: {template_name}")
            return None
    
    def render_template(self, template_name, **kwargs):
        """
        Render a template with the provided variables
        
        Args:
            template_name (str): Name of the template to render
            **kwargs: Variables to render in the template
            
        Returns:
            str: Rendered template or None if template not found
        """
        template_data = self.get_template(template_name)
        if not template_data or 'template' not in template_data:
            return None
        
        template = template_data['template']
        
        # Simple string formatting for template variables
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing variable in template {template_name}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {str(e)}")
            return None
    
    def reload_templates(self):
        """Reload all templates from disk"""
        self.templates = {}
        self._load_templates()
        
    def save_template(self, template_name, template_data):
        """
        Save a template to disk
        
        Args:
            template_name (str): Name of the template
            template_data (dict): Template data to save
            
        Returns:
            bool: Success or failure
        """
        try:
            template_path = self.templates_dir / f"{template_name}.json"
            with open(template_path, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            # Update in-memory cache
            self.templates[template_name] = template_data
            logger.info(f"Saved template: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving template {template_name}: {str(e)}")
            return False

# Initialize a global template manager instance
template_manager = PromptTemplateManager()