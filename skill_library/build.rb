require 'yaml'

module SkillLibrary
  PUBLIC_FIELDS = %w[id name description inputs requires achieves outcomes].freeze
  REQUIRED_FIELDS = (PUBLIC_FIELDS + %w[executor verifier]).freeze

  def self.load_yaml(path)
    YAML.safe_load(File.read(path))
  end

  def self.build(root)
    types = load_yaml(File.join(root, 'types.yaml')).fetch('types')
    source_files = Dir[File.join(root, 'skills', '*.yaml')].sort
    raise 'No skill contracts found' if source_files.empty?

    contracts = source_files.map { |path| load_yaml(path) }
    ids = contracts.map { |contract| contract.fetch('id') }
    raise 'Duplicate skill ID' unless ids.uniq == ids

    contracts.each do |contract|
      missing = REQUIRED_FIELDS - contract.keys
      raise "#{contract['id']}: missing #{missing.join(', ')}" unless missing.empty?
      unknown = contract.fetch('inputs').values - types.keys
      raise "#{contract['id']}: unknown input types #{unknown.join(', ')}" unless unknown.empty?
    end

    connections = contracts.flat_map do |contract|
      contract.fetch('connections', []).map do |link|
        targets = link.fetch('to')
        raise "#{contract['id']}: unknown connection target" unless targets.is_a?(Array) &&
          !targets.empty? && targets.all? { |target| ids.include?(target) }
        { 'from' => contract.fetch('id'), 'to' => targets,
          'when' => link.fetch('when') }
      end
    end

    public_skills = contracts.map do |contract|
      PUBLIC_FIELDS.each_with_object({}) { |field, entry| entry[field] = contract.fetch(field) }
    end

    { 'version' => 1,
      'description' => 'Complete model-facing ZenoBench Skill Library. Each skill has one authoritative source contract under skills/.',
      'types' => types, 'skills' => public_skills,
      'connections' => connections }
  end
end

if __FILE__ == $PROGRAM_NAME
  root = File.expand_path(__dir__)
  File.write(File.join(root, 'skill_library.yaml'), YAML.dump(SkillLibrary.build(root)))
end
