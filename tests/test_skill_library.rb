require 'minitest/autorun'
require 'yaml'
require_relative '../skill_library/build'

class SkillLibraryTest < Minitest::Test
  ROOT = File.expand_path('../skill_library', __dir__)

  def test_aggregate_contains_every_authoritative_skill_and_connection
    source_files = Dir[File.join(ROOT, 'skills', '*.yaml')].sort
    source_ids = source_files.map { |path| YAML.safe_load(File.read(path)).fetch('id') }
    aggregate = SkillLibrary.build(ROOT)

    assert_equal source_ids.sort, aggregate.fetch('skills').map { |skill| skill.fetch('id') }.sort
    assert_equal source_files.sum { |path| YAML.safe_load(File.read(path)).fetch('connections', []).length },
                 aggregate.fetch('connections').length
    assert_equal aggregate, YAML.safe_load(File.read(File.join(ROOT, 'skill_library.yaml')))
  end

  def test_aggregate_exposes_capabilities_without_runtime_code
    aggregate = SkillLibrary.build(ROOT)

    refute_empty aggregate.fetch('skills')
    aggregate.fetch('skills').each do |skill|
      assert (skill.keys & %w[executor verifier]).empty?
      assert skill.key?('id')
      assert skill.key?('name')
    end
    refute_match(/zeno_skills|callable:|invocation:/, YAML.dump(aggregate))
  end
end
