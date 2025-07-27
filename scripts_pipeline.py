import os
import re

# Safe import of folder_paths with fallback
try:
    import folder_paths
except ImportError:
    # Fallback for when not in ComfyUI environment
    class folder_paths:
        base_path = os.getcwd()

### SET MAIN CHANNEL NODE

class SetMainChannel:
    """Universal Styler channel management node for pipeline organization and workflow tracking."""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "channel": ("STRING", {"default": "CH_0001", "multiline":False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("channel output",)
    FUNCTION = "set_mainchannel"
    CATEGORY = "Universal-Styler"
    DESCRIPTION = "Set and manage channel IDs for Universal Styler pipeline organization"

    def set_mainchannel(self, channel):
        return (channel,)


### SAVE SCRIPT NODE

class SaveScriptToDatabase:
    """Save custom prompt scripts to Universal Styler CSV databases for prompting and scene management."""
    
    @classmethod  
    def INPUT_TYPES(cls):
        return {
            "required": {
                "script_name": ("STRING", {"default": "New Script", "multiline": False}),
                "short_prompt": ("STRING", {"default": "short description", "multiline": True}),
                "long_prompt": ("STRING", {"default": "detailed description", "multiline": True}),
                "csv_type": (["agents", "scenes", "motions", "cameras", "lightings", "styles"],),
                "overwrite_existing": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING",)
    RETURN_NAMES = ("status", "saved_to", "script_name",)
    FUNCTION = "save_script"
    CATEGORY = "Universal-Styler"
    DESCRIPTION = "Save prompt scripts to Universal Styler CSV databases (agents, scenes, motions, cameras, lightings, styles)"
    OUTPUT_NODE = True

    def save_script(self, script_name, short_prompt, long_prompt, csv_type, overwrite_existing):
        try:
            # Get the CSV file path
            base = os.path.dirname(__file__)
            csv_path = os.path.join(base, "SCRIPTS", f"{csv_type}.csv")
            
            # Validate inputs
            if not script_name.strip():
                return ("ERROR: Script name cannot be empty", csv_type, script_name)
            
            script_name = script_name.strip()
            short_prompt = short_prompt.strip()
            long_prompt = long_prompt.strip()
            
            # Read existing CSV data
            existing_data = []
            header = "name,short_prompt,long_prompt"
            
            if os.path.exists(csv_path):
                try:
                    with open(csv_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if lines:
                            header = lines[0].strip()
                            for line in lines[1:]:
                                line = line.strip()
                                if line:
                                    existing_data.append(line)
                except Exception as e:
                    print(f"Warning: Could not read existing {csv_type}.csv: {e}")
            
            # Check if script name already exists
            script_exists = False
            for i, line in enumerate(existing_data):
                try:
                    # Parse existing line
                    fields = [x.replace('"', '').strip() for x in re.split(',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)]
                    if len(fields) >= 1 and fields[0] == script_name:
                        script_exists = True
                        if overwrite_existing:
                            # Update existing entry
                            new_line = self._format_csv_line(script_name, short_prompt, long_prompt)
                            existing_data[i] = new_line
                            break
                        else:
                            return (f"ERROR: Script '{script_name}' already exists. Enable 'Overwrite Existing' to update.", csv_type, script_name)
                except:
                    continue
            
            # Add new entry if it doesn't exist
            if not script_exists:
                new_line = self._format_csv_line(script_name, short_prompt, long_prompt)
                existing_data.append(new_line)
            
            # Write back to CSV file
            try:
                with open(csv_path, "w", encoding="utf-8") as f:
                    f.write(header + "\n")
                    for line in existing_data:
                        f.write(line + "\n")
                
                # Clear the CSV cache to force reload in Load Scripts node
                if hasattr(LoadScriptsFromDatabase, '_csv_loaded'):
                    LoadScriptsFromDatabase._csv_loaded = False
                    # Clear all CSV data to force complete reload
                    LoadScriptsFromDatabase.agents_csv = {}
                    LoadScriptsFromDatabase.scenes_csv = {}
                    LoadScriptsFromDatabase.motions_csv = {}
                    LoadScriptsFromDatabase.lightings_csv = {}
                    LoadScriptsFromDatabase.styles_csv = {}
                    LoadScriptsFromDatabase.cameras_csv = {}
                
                action = "Updated" if script_exists and overwrite_existing else "Added"
                status_msg = f"SUCCESS: {action} '{script_name}' to {csv_type}.csv"
                print(f"ComfyUI Universal Styler: {status_msg}")
                
                return (status_msg, f"{csv_type}.csv", script_name)
                
            except Exception as e:
                error_msg = f"ERROR: Could not write to {csv_type}.csv: {str(e)}"
                print(f"ComfyUI Universal Styler: {error_msg}")
                return (error_msg, csv_type, script_name)
                
        except Exception as e:
            error_msg = f"ERROR: Failed to save script: {str(e)}"
            print(f"ComfyUI Universal Styler: {error_msg}")
            return (error_msg, csv_type, script_name)
    
    def _format_csv_line(self, name, short, long):
        """Format a CSV line with proper escaping"""
        def escape_field(field):
            # Escape quotes and wrap in quotes if contains comma
            field = str(field).replace('"', '""')
            if ',' in field or '"' in field or '\n' in field:
                return f'"{field}"'
            return field
        
        return f"{escape_field(name)},{escape_field(short)},{escape_field(long)}"


### LOAD SCIPTS NODE

class LoadScriptsFromDatabase:
    """Load and compile prompt scripts from Universal Styler CSV databases for prompting with agents, scenes, motions, cameras, lighting, and styles."""
    
    @staticmethod
    def load_csv_database(csv_path: str, csv_type: str):
        """Generic CSV loader for all database types.
        Args:
            csv_path: Path to the CSV file
            csv_type: Type name for error messages (e.g., 'agents', 'scenes')
        Returns: Dict with script_name as key and [short_script, long_script] as value
        """
        # More resilient fallback data
        fallback_data = {
            f"Default {csv_type.title()}": [f"Default {csv_type}", f"Default {csv_type} description"],
            f"Select {csv_type}...": ["", ""]
        }
        
        if not os.path.exists(csv_path):
            print(f"Warning: {csv_type}.csv not found at {csv_path}. Using fallback data.")
            return fallback_data
            
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[1:]  # Skip header
                csv_data = []
                for line in lines:
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                    # Parse CSV line handling quoted fields
                    fields = [x.replace('"', '').replace('\n','') for x in re.split(',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)]
                    if len(fields) >= 3:  # Ensure we have at least 3 columns
                        csv_data.append(fields)
                
                result = {x[0]: [x[1], x[2]] for x in csv_data if len(x) >= 3 and x[0].strip()}
                
                # Ensure we always have at least one entry
                if not result:
                    return fallback_data
                    
                return result
                
        except Exception as e:
            print(f"Warning: Error loading {csv_type}.csv: {e}. Using fallback data.")
            return fallback_data

    # LOAD AGENTS FROM DATABASE
    @staticmethod
    def load_agents_csv(agents_path: str):
        """Loads AGENTS Database file (CSV). It has three columns. It Ignores the first row (header).
        Returns: Dict of scripts. Each script is a dict with keys: script_name and value: [short_script, long_script]
        """
        return LoadScriptsFromDatabase.load_csv_database(agents_path, "agents")
    
    # LOAD SCENES FROM DATABASE
    @staticmethod
    def load_scenes_csv(scenes_path: str):
        """Loads SCENES Database file (CSV). It has three columns. It Ignores the first row (header).
        Returns: Dict of scripts. Each script is a dict with keys: script_name and value: [short_script, long_script]
        """
        return LoadScriptsFromDatabase.load_csv_database(scenes_path, "scenes")

    # LOAD MOTION FROM DATABASE
    @staticmethod
    def load_motions_csv(motions_path: str):
        """Loads MOTIONS Database file (CSV). It has three columns. It Ignores the first row (header).
        Returns: Dict of scripts. Each script is a dict with keys: script_name and value: [short_script, long_script]
        """
        return LoadScriptsFromDatabase.load_csv_database(motions_path, "motions")
    
    # LOAD LIGHTINGS FROM DATABASE
    @staticmethod
    def load_lightings_csv(lightings_path: str):
        """Loads LIGHTINGS Database file (CSV). It has three columns. It Ignores the first row (header).
        Returns: Dict of scripts. Each script is a dict with keys: script_name and value: [short_script, long_script]
        """
        return LoadScriptsFromDatabase.load_csv_database(lightings_path, "lightings")
    
    # LOAD STYLES FROM DATABASE
    @staticmethod
    def load_styles_csv(styles_path: str):
        """Loads STYLES Database file (CSV). It has three columns. It Ignores the first row (header).
        Returns: Dict of scripts. Each script is a dict with keys: script_name and value: [short_script, long_script]
        """
        return LoadScriptsFromDatabase.load_csv_database(styles_path, "styles")
    
    # LOAD CAMERAS FROM DATABASE
    @staticmethod
    def load_cameras_csv(cameras_path: str):
        """Loads CAMERAS Database file (CSV). It has three columns. It Ignores the first row (header).
        Returns: Dict of scripts. Each script is a dict with keys: script_name and value: [short_script, long_script]
        """
        return LoadScriptsFromDatabase.load_csv_database(cameras_path, "cameras")
        
    # CUSTOM NODES SETUP
    
    @classmethod
    def get_default_inputs(cls):
        """Get default/safe input values for the node"""
        cls.load_csv_data()
        return {
            "prompt_type": "Short Prompt",
            "output_format": "Compiled", 
            "agents": list(cls.agents_csv.keys())[0] if cls.agents_csv else "Default Agent",
            "styles": list(cls.styles_csv.keys())[0] if cls.styles_csv else "Default Style",
            "motions": list(cls.motions_csv.keys())[0] if cls.motions_csv else "Default Motion",
            "cameras": list(cls.cameras_csv.keys())[0] if cls.cameras_csv else "Default Camera",
            "lightings": list(cls.lightings_csv.keys())[0] if cls.lightings_csv else "Default Lighting",
            "scenes": list(cls.scenes_csv.keys())[0] if cls.scenes_csv else "Default Scene"
        }
    
    @classmethod 
    def load_csv_data(cls, force_reload=False):
        """Load CSV data safely with error handling"""
        if hasattr(cls, '_csv_loaded') and cls._csv_loaded and not force_reload:
            return
            
        try:
            base = os.path.dirname(__file__)
            print(f"ComfyUI Universal Styler: Loading CSV files from {base}/SCRIPTS/")
            
            cls.agents_csv = cls.load_agents_csv(os.path.join(base, "SCRIPTS", "agents.csv"))
            cls.scenes_csv = cls.load_scenes_csv(os.path.join(base, "SCRIPTS", "scenes.csv"))
            cls.motions_csv = cls.load_motions_csv(os.path.join(base, "SCRIPTS", "motions.csv"))
            cls.lightings_csv = cls.load_lightings_csv(os.path.join(base, "SCRIPTS", "lightings.csv"))
            cls.styles_csv = cls.load_styles_csv(os.path.join(base, "SCRIPTS", "styles.csv"))
            cls.cameras_csv = cls.load_cameras_csv(os.path.join(base, "SCRIPTS", "cameras.csv"))
            
            # Log loaded data counts
            total_items = (len(cls.agents_csv) + len(cls.scenes_csv) + len(cls.motions_csv) + 
                          len(cls.lightings_csv) + len(cls.styles_csv) + len(cls.cameras_csv))
            print(f"ComfyUI Universal Styler: Successfully loaded {total_items} total script items")
            
            cls._csv_loaded = True
        except Exception as e:
            print(f"ComfyUI Universal Styler: Error loading CSV files: {e}")
            # Provide fallback data
            cls.agents_csv = {"Default Agent": ["default agent", "default agent description"]}
            cls.scenes_csv = {"Default Scene": ["default scene", "default scene description"]}
            cls.motions_csv = {"Default Motion": ["default motion", "default motion description"]}
            cls.lightings_csv = {"Default Lighting": ["default lighting", "default lighting description"]}
            cls.styles_csv = {"Default Style": ["default style", "default style description"]}
            cls.cameras_csv = {"Default Camera": ["default camera", "default camera description"]}
            print("ComfyUI Universal Styler: Using fallback data")
            cls._csv_loaded = True

    @classmethod
    def INPUT_TYPES(cls):
        cls.load_csv_data()
        
        # Ensure we always have at least one option for each dropdown
        def safe_keys(csv_dict, fallback_name):
            keys = list(csv_dict.keys())
            return keys if keys else [f"No {fallback_name} available"]
        
        return {
            "required": {
                "channel_input": ("STRING", {"forceInput": True}),
                "prompt_type": (["Short Prompt", "Long Prompt"], {"default": "Short Prompt"}),
                "output_format": (["Compiled", "Solo Agent", "Experimental Tags"], {"default": "Compiled"}),
                "randomize": (["Disabled", "All Categories", "Agents Only", "Styles Only", "Technical Only"], {"default": "Disabled"}),
                "agents": (safe_keys(cls.agents_csv, "agents"),),
                "scenes": (safe_keys(cls.scenes_csv, "scenes"),),
                "script_prefix": ("STRING", {"multiline": False,"default": ""}),
                "cameras": (safe_keys(cls.cameras_csv, "cameras"),),
                "motions": (safe_keys(cls.motions_csv, "motions"),),
                "styles": (safe_keys(cls.styles_csv, "styles"),),
                "lightings": (safe_keys(cls.lightings_csv, "lightings"),),
                "channel_follow": ("STRING", {"multiline": False,"default": "#0001"}),
                "channel_encode": ("BOOLEAN", {"default": False}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            },                
        }
    
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Force refresh when CSV files change or when randomize is enabled"""
        import random
        import time
        
        seed = kwargs.get('seed', 0)
        randomize = kwargs.get('randomize', 'Disabled')
        
        # If randomization is enabled, always refresh to get new random selections
        if randomize != 'Disabled':
            # Use seed + random element to force refresh each time
            return random.randint(0, 0xffffffffffffffff) + seed
        
        # Check file modification times and force refresh if files changed
        base = os.path.dirname(__file__)
        csv_files = ["agents.csv", "scenes.csv", "motions.csv", "lightings.csv", "styles.csv", "cameras.csv"]
        
        current_time = 0
        for csv_file in csv_files:
            path = os.path.join(base, "SCRIPTS", csv_file)
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                current_time = max(current_time, mtime)
        
        # Store last known modification time
        if not hasattr(cls, '_last_mod_time'):
            cls._last_mod_time = current_time
            
        # If files have been modified, force reload
        if current_time > cls._last_mod_time:
            cls._last_mod_time = current_time
            cls._csv_loaded = False
            print("ComfyUI Universal Styler: CSV files changed, forcing reload")
            return float("inf")
        
        # Use seed and other parameters for change detection
        prompt_type = kwargs.get('prompt_type', 'Short Prompt')
        timestamps = [prompt_type, str(seed), str(current_time)]
        
        return hash(tuple(timestamps))

    RETURN_TYPES = ("STRING","STRING",)
    RETURN_NAMES = ("channel output", "script output",)
    FUNCTION = "load_scripts"
    CATEGORY = "Universal-Styler"
    DESCRIPTION = "Load and compile prompt scripts from CSV databases with selectable short/long prompts for prompting (agents, scenes, motions, cameras, lighting, styles)"   

    def load_scripts(self, script_prefix, channel_input, prompt_type, output_format, randomize, agents, styles, motions, cameras, lightings, scenes, channel_follow, channel_encode, seed=0):
        try:
            
            # Ensure CSV data is loaded for this instance
            self.__class__.load_csv_data()
            
            # Handle randomization if enabled
            import random
            if randomize != 'Disabled':
                # Set random seed for consistent randomization in this execution
                random.seed(seed)
                
                # Get available options (excluding default/select entries)
                def get_random_selection(csv_data, exclude_prefixes=["Select", "Default", "No "]):
                    available_options = [key for key in csv_data.keys() 
                                       if not any(key.startswith(prefix) for prefix in exclude_prefixes)]
                    return random.choice(available_options) if available_options else list(csv_data.keys())[0]
                
                # Apply randomization based on mode
                if randomize == "All Categories":
                    agents = get_random_selection(self.__class__.agents_csv)
                    styles = get_random_selection(self.__class__.styles_csv)
                    motions = get_random_selection(self.__class__.motions_csv)
                    cameras = get_random_selection(self.__class__.cameras_csv)
                    lightings = get_random_selection(self.__class__.lightings_csv)
                    scenes = get_random_selection(self.__class__.scenes_csv)
                    print(f"ComfyUI Universal Styler: Randomized all categories - Agent: {agents}, Style: {styles}")
                    
                elif randomize == "Agents Only":
                    agents = get_random_selection(self.__class__.agents_csv)
                    print(f"ComfyUI Universal Styler: Randomized agent: {agents}")
                    
                elif randomize == "Styles Only":
                    styles = get_random_selection(self.__class__.styles_csv)
                    print(f"ComfyUI Universal Styler: Randomized style: {styles}")
                    
                elif randomize == "Technical Only":
                    motions = get_random_selection(self.__class__.motions_csv)
                    cameras = get_random_selection(self.__class__.cameras_csv)
                    lightings = get_random_selection(self.__class__.lightings_csv)
                    scenes = get_random_selection(self.__class__.scenes_csv)
                    print(f"ComfyUI Universal Styler: Randomized technical - Motion: {motions}, Camera: {cameras}")
            
            # Validate and fix inputs - use first available if invalid
            def validate_or_default(value, csv_data, csv_type):
                if value in csv_data:
                    return value
                else:
                    available_keys = list(csv_data.keys())
                    default_key = available_keys[0] if available_keys else f"Default {csv_type}"
                    print(f"ComfyUI Universal Styler: '{value}' not found in {csv_type}, using '{default_key}'")
                    return default_key
            
            # Validate all inputs and use defaults if invalid
            agents = validate_or_default(agents, self.__class__.agents_csv, "agents")
            styles = validate_or_default(styles, self.__class__.styles_csv, "styles")
            motions = validate_or_default(motions, self.__class__.motions_csv, "motions")
            cameras = validate_or_default(cameras, self.__class__.cameras_csv, "cameras")
            lightings = validate_or_default(lightings, self.__class__.lightings_csv, "lightings")
            scenes = validate_or_default(scenes, self.__class__.scenes_csv, "scenes")
            
            # Convert user-friendly output format labels to internal values
            output_format_map = {
                "Compiled": "compiled",
                "Solo Agent": "solo_agent", 
                "Experimental Tags": "experimental_tags"
            }
            internal_format = output_format_map.get(output_format, "compiled")
            if output_format not in output_format_map:
                print(f"ComfyUI Universal Styler: Invalid output_format '{output_format}', using 'Compiled'")
                internal_format = "compiled"
            
            # Determine which prompt column to use (0=short, 1=long)
            # Convert user-friendly labels to internal values
            prompt_index = 0 if prompt_type == "Short Prompt" else 1
            
            # Build prompts based on selected type
            prompt_parts = [
                script_prefix,
                self.__class__.agents_csv[agents][prompt_index],
                self.__class__.motions_csv[motions][prompt_index],
                self.__class__.cameras_csv[cameras][prompt_index], 
                self.__class__.scenes_csv[scenes][prompt_index],
                self.__class__.styles_csv[styles][prompt_index],
                self.__class__.lightings_csv[lightings][prompt_index]
            ]
            compiled_prompt = " ".join(part for part in prompt_parts if part.strip())

            channel_concat = f"{channel_input}/{channel_follow}"
            
            # Determine output channel
            output_channel = channel_concat if channel_encode else channel_follow
            
            # Format output based on internal_format
            if internal_format == "compiled":
                final_output = compiled_prompt
            elif internal_format == "solo_agent":
                final_output = f"AGENT: {self.__class__.agents_csv[agents][prompt_index]}/DETAILS: {self.__class__.agents_csv[agents][1]}"  # Always use long for details
            elif internal_format == "experimental_tags":
                final_output = f"{channel_concat}/ SCE/ {self.__class__.scenes_csv[scenes][prompt_index]}/ MOT/ {self.__class__.motions_csv[motions][prompt_index]}/ CAM/ {self.__class__.cameras_csv[cameras][prompt_index]}/ AGT/ {self.__class__.agents_csv[agents][prompt_index]}/ STL/ {self.__class__.styles_csv[styles][prompt_index]}/ LGT/ {self.__class__.lightings_csv[lightings][prompt_index]}"
            else:
                final_output = compiled_prompt
            
            return (output_channel, final_output)
            
        except Exception as e:
            print(f"Error in load_scripts: {e}")
            return (channel_follow, f"Error loading scripts: {str(e)}")
            

# ComfyUI 2025 Node Registration
# Using proper node class registration with better organization

NODE_CLASS_MAPPINGS = {
    "UniversalStyler_SetMainChannel": SetMainChannel,
    "UniversalStyler_LoadScriptsFromDatabase": LoadScriptsFromDatabase,
    "UniversalStyler_SaveScriptToDatabase": SaveScriptToDatabase,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UniversalStyler_SetMainChannel": "Universal Styler - Set Channel ID (Pipeline Management)",
    "UniversalStyler_LoadScriptsFromDatabase": "Universal Styler - Load Scripts (Short/Long Prompts Database CSV)", 
    "UniversalStyler_SaveScriptToDatabase": "Universal Styler - Save Prompt Script (CSV Database Management)",
}

# Input parameter display names for better UI readability
INPUT_DISPLAY_NAMES = {
    "prompt_type": "Prompt Type",
    "output_format": "Output Format", 
    "randomize": "Randomize Categories",
    "script_prefix": "Script Prefix",
    "channel_input": "Channel Input",
    "channel_follow": "Channel Follow",
    "channel_encode": "Channel Encode"
}

# Search aliases for better discoverability 
WEB_DIRECTORY = "./web"

# Export for ComfyUI 2025 compatibility
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
