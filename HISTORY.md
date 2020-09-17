T2WML API History
===================================
Changes in version wip:
------------------------
* validate P/Q node definitions (must begin with P/Q, Pnum where num<10000 or Qnum where num<1 billion not allowed)
* when fetching property type, fetch description and label while you're at it
* stop saving directory to project file

Changes in version 0.0.12:
------------------------
* deprecation: rename add_nodes_from_file to add_entities_from_file
* backwards incompatible: rename .t2wmlproj to project.t2wml, so that it can be viewed on mac and linux
* change default project title from "Untitled" to folder name

Changes in version 0.0.11:
------------------------
* rename add_wikidata_file to more accurate add_entity_file

Changes in version 0.0.10:
------------------------
* All at least somewhat backwards incompatible:
    * Changed project class filename to .t2wmlproj
    * added sparql endpoint and warn for empty cells settings to project
    * change add_properties_from_file to add_nodes_from_file, some changes to wikidata_provider interface (documented in api.md)
    * change returned dict key (from adding properties to file) from "present" to "updated"
* Bug fix:
    * when set to something like $sheet, which doesn't return ReturnClass, parsing would fail on attribute error

Changes in version 0.0.8:
------------------------
* added the Project class
* change settings to be class-based instead of a dictionary
* add setting `cache_data_files_folder`
* when caching, use an underscored version of the full path to the original file to create the cache name
* add setting `warn_for_empty_cells`, default False
* change how date parsing is handled: if format is provided, must stricly match format, otherwise will fuzzy-guess
* change default behavior for regex to return first group

Changes in version 0.0.7:
-------------------------
* support utf-8 encoding for yaml files
* bug fixes:
  - bug fix for spacey import errors
  - fixed bug reading value definitions in wikifier where value is numeric
  - read pandas dataframes as strings (fixes bug: Object of type Timestamp is not JSON serializable)
  - do not re-apply same skips (fixes bug: Multiple skip_rows conditions that apply to the same row causes error)
  - do not generate qualifier edges for empty values
  - empty data cells were not being skipped
  - skip cells were being saved in columns
  - "node2;kgtk:data_type" for location changed from "coordinate" to "location_coordinate"
  - added globe field to kgtk output
* change settings to be class-based instead of a dictionary
* add setting `cache_data_files_folder`
* when caching, use an underscored version of the full path to the original file to create the cache name

Changes in version 0.0.6:
-------------------------
* complete overhaul of region definition, added support for 'columns'/'rows'/'cells'
* backwards incompatible: 
     * changed 'skip_column/row/cell' to 'skip_columns/rows/cells'
     * renamed BaseStatementMapper to StatementMapper
     * KnowledgeGraph.save_download renamed to KnowledgeGraph.save_file
* added case insensitivity to property typing (ie, url, Url, URL now all valid)
* stop printing template errors
* bug fixes:
  - critical bug: did not recognise 0 column/0 row when wikifying
  - x->y is now valid (previously only worked with spaces, x -> y)
  - error when not sending any date formats
  - item and cell falsiness now explicitly defined

Changes in version 0.0.5:
-------------------------

* add support for list of date formats
* etk is now optional
* class SpreadsheetFile has been refined
* added class Statement
* statements are returned if they are valid (no errors in value, property, and item)
* qualifiers are included if they are valid (no errors in value, property)
* yet more docs, examples, tests

Changes in version 0.0.4:
-------------------------

* A lot more classes:
    - Wikifier class fully working, supports multiple wikifier definitions
    - ItemTable completely revamped, totally different storage and lookup mechanism including preferential lookup
    - Revamp of cell mapping, now with base class BaseStatementMapper and implementation YamlMapper
    - WikifierService class 

Changes in version 0.0.3:
------------------------

* DataFile is now SpreadsheetFile
* bug fix:  bad access to sparql endpoint
* add support for adding label and description when uploading properties in tsv

Changes in version 0.0.2:
-------------------------

* when wikify_region fails on specific cells, return error listing those cells, and wikify the rest
* create temporary csv with tempfile rather than manually
* add support for $filename to t2wml syntax
* add support for Url as property type
* do not include project name in kgtk id
* add metadata (sheet and filename) to results
* continued cleaning of server-specific code from the API

Changes in version 0.0.1:
-------------------------

* separated from the server code into own package
